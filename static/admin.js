// ==============================================================
// GRAND AZURE CONTROL PANEL & INVENTORY MANAGEMENT
// ==============================================================

// Auth Check: Redirect to login if unauthenticated
if (!localStorage.getItem("northstar_auth_token")) {
  window.location.replace("/?redirect=/admin");
}

document.addEventListener("DOMContentLoaded", async () => {
  // Set default dates for the availability tester
  const today = new Date();
  const tomorrow = new Date(today);
  tomorrow.setDate(today.getDate() + 1);
  const dayAfter = new Date(today);
  dayAfter.setDate(today.getDate() + 3);

  const cinInput = document.getElementById("avail-cin");
  const coutInput = document.getElementById("avail-cout");
  if (cinInput && !cinInput.value) cinInput.value = tomorrow.toISOString().split("T")[0];
  if (coutInput && !coutInput.value) coutInput.value = dayAfter.toISOString().split("T")[0];

  // Initial Data Load
  await loadStats();
  await loadLocationsTable();
  await loadLocationsDropdown();
  await loadHotelsDropdown();
});

// Tab Switcher
function switchAdminTab(tabName) {
  const tabs = ["locations", "hotels", "rooms", "bookings"];
  const buttons = document.querySelectorAll(".tab-btn");

  tabs.forEach((t, idx) => {
    const content = document.getElementById(`tab-${t}`);
    if (content) {
      if (t === tabName) {
        content.classList.add("active");
        if (buttons[idx]) buttons[idx].classList.add("active");
      } else {
        content.classList.remove("active");
        if (buttons[idx]) buttons[idx].classList.remove("active");
      }
    }
  });

  // Trigger specific data refresh
  if (tabName === "locations") {
    loadLocationsTable();
  } else if (tabName === "hotels") {
    loadHotelsTable();
    loadLocationsDropdown();
  } else if (tabName === "rooms") {
    loadRoomsTable();
    loadHotelsDropdown();
  } else if (tabName === "bookings") {
    loadBookingsTable();
    loadHotelAndRoomsForAvailability();
  }
}

// ==============================================================
// 1. STATS OVERVIEW
// ==============================================================
async function loadStats() {
  try {
    const res = await fetch("/api/admin/stats");
    const data = await res.json();
    if (data.success && data.stats) {
      const s = data.stats;
      document.getElementById("stat-locations-count").textContent = s.locations_count || 0;
      document.getElementById("stat-hotels-count").textContent = s.hotels_count || 0;
      document.getElementById("stat-rooms-count").textContent = s.rooms_count || 0;
      document.getElementById("stat-bookings-count").textContent = s.bookings_count || 0;
      document.getElementById("stat-transfers-count").textContent = (s.airport_pickups || 0) + (s.airport_drops || 0);
    }
  } catch (err) {
    console.error("Failed to load admin stats:", err);
  }
}

// ==============================================================
// 2. LOCATIONS MANAGEMENT
// ==============================================================
async function loadLocationsTable() {
  const tbody = document.getElementById("tbody-locations");
  if (!tbody) return;
  tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; padding: 20px;"><i class="fa-solid fa-circle-notch fa-spin"></i> Loading locations...</td></tr>`;

  try {
    const res = await fetch("/api/locations");
    const data = await res.json();
    if (data.success && data.locations && data.locations.length > 0) {
      tbody.innerHTML = data.locations.map(loc => `
        <tr>
          <td><strong style="color: var(--primary);">${escapeHtml(loc.location_id)}</strong></td>
          <td><strong style="color: var(--text-main);">${escapeHtml(loc.city)}</strong></td>
          <td><span class="badge-code">${escapeHtml(loc.airport_code)}</span></td>
          <td>${escapeHtml(loc.airport_name)}</td>
          <td>${escapeHtml(loc.country || '')}</td>
          <td>
            <button class="btn-delete-booking" onclick="deleteLocation('${loc.location_id}')">
              <i class="fa-solid fa-trash"></i> Delete
            </button>
          </td>
        </tr>
      `).join("");
    } else {
      tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: #94a3b8; padding: 20px;">No airport locations registered yet. Add one above!</td></tr>`;
    }
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="6" style="color: #ef4444; text-align: center;">Failed to load locations.</td></tr>`;
  }
}

async function handleAddLocation(e) {
  e.preventDefault();
  const city = document.getElementById("loc-city").value.trim();
  const airport_name = document.getElementById("loc-airport-name").value.trim();
  const airport_code = document.getElementById("loc-airport-code").value.trim().toUpperCase();
  const country = document.getElementById("loc-country").value.trim();

  if (!city || !airport_name || !airport_code) {
    alert("Please fill in City, Airport Name, and Airport Code.");
    return;
  }

  try {
    const res = await fetch("/api/locations", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        location_id: `LOC-${airport_code}`,
        city,
        airport_name,
        airport_code,
        country
      })
    });
    const result = await res.json();
    if (result.success) {
      document.getElementById("form-add-location").reset();
      await loadLocationsTable();
      await loadLocationsDropdown();
      await loadStats();
      alert(`Location ${city} (${airport_code}) saved successfully to MongoDB!`);
    } else {
      alert("Error adding location: " + (result.detail || result.message));
    }
  } catch (err) {
    alert("Request failed: " + err.message);
  }
}

async function deleteLocation(locationId) {
  if (!confirm(`Are you sure you want to delete location ${locationId}? This will also delete hotels and rooms associated with it.`)) return;
  try {
    const res = await fetch(`/api/locations/${locationId}`, { method: "DELETE" });
    const result = await res.json();
    if (result.success) {
      await loadLocationsTable();
      await loadLocationsDropdown();
      await loadHotelsTable();
      await loadStats();
    }
  } catch (err) {
    alert("Delete failed: " + err.message);
  }
}

async function loadLocationsDropdown() {
  const select = document.getElementById("hotel-location-select");
  if (!select) return;
  try {
    const res = await fetch("/api/locations");
    const data = await res.json();
    if (data.success && data.locations) {
      select.innerHTML = data.locations.map(l => `
        <option value="${l.location_id}">${l.city} (${l.airport_code}) - ${l.airport_name}</option>
      `).join("");
    }
  } catch (err) {
    console.error("Failed to load locations select:", err);
  }
}

// ==============================================================
// 3. HOTELS MANAGEMENT
// ==============================================================
async function loadHotelsTable() {
  const tbody = document.getElementById("tbody-hotels");
  if (!tbody) return;
  tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; padding: 20px;"><i class="fa-solid fa-circle-notch fa-spin"></i> Loading hotels...</td></tr>`;

  try {
    const res = await fetch("/api/hotels");
    const data = await res.json();
    if (data.success && data.hotels && data.hotels.length > 0) {
      tbody.innerHTML = data.hotels.map(h => `
        <tr>
          <td><strong style="color: var(--primary);">${escapeHtml(h.hotel_id)}</strong></td>
          <td><strong style="color: var(--text-main);">${escapeHtml(h.name)}</strong></td>
          <td><span class="badge-code">${escapeHtml(h.location_id)}</span></td>
          <td><small style="color: var(--text-muted);">${escapeHtml(h.address)}</small></td>
          <td><span style="color: #d97706; font-weight: 700;">★ ${h.rating || '4.8'}</span></td>
          <td>
            <button class="btn-delete-booking" onclick="deleteHotel('${h.hotel_id}')">
              <i class="fa-solid fa-trash"></i> Delete
            </button>
          </td>
        </tr>
      `).join("");
    } else {
      tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: #94a3b8; padding: 20px;">No hotels found. Add a new hotel above!</td></tr>`;
    }
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="6" style="color: #ef4444; text-align: center;">Failed to load hotels.</td></tr>`;
  }
}

async function handleAddHotel(e) {
  e.preventDefault();
  const location_id = document.getElementById("hotel-location-select").value;
  const name = document.getElementById("hotel-name").value.trim();
  const address = document.getElementById("hotel-address").value.trim();
  const rating = parseFloat(document.getElementById("hotel-rating").value) || 4.8;
  const description = document.getElementById("hotel-desc").value.trim();

  if (!location_id || !name || !address) {
    alert("Please fill in destination location, hotel name, and address.");
    return;
  }

  try {
    const res = await fetch("/api/hotels", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        location_id,
        name,
        address,
        rating,
        description
      })
    });
    const result = await res.json();
    if (result.success) {
      document.getElementById("form-add-hotel").reset();
      await loadHotelsTable();
      await loadHotelsDropdown();
      await loadStats();
      alert(`Hotel '${name}' added successfully to MongoDB!`);
    } else {
      alert("Error adding hotel: " + (result.detail || result.message));
    }
  } catch (err) {
    alert("Request failed: " + err.message);
  }
}

async function deleteHotel(hotelId) {
  if (!confirm(`Are you sure you want to delete hotel ${hotelId}? Associated rooms will also be deleted.`)) return;
  try {
    const res = await fetch(`/api/hotels/${hotelId}`, { method: "DELETE" });
    const result = await res.json();
    if (result.success) {
      await loadHotelsTable();
      await loadHotelsDropdown();
      await loadRoomsTable();
      await loadStats();
    }
  } catch (err) {
    alert("Delete failed: " + err.message);
  }
}

async function loadHotelsDropdown() {
  const roomHotelSelect = document.getElementById("room-hotel-select");
  const filterRoomHotel = document.getElementById("filter-room-hotel");
  const availHotelSelect = document.getElementById("avail-hotel-select");

  try {
    const res = await fetch("/api/hotels");
    const data = await res.json();
    if (data.success && data.hotels) {
      const optionsHtml = data.hotels.map(h => `
        <option value="${h.hotel_id}">${h.name} (${h.location_id})</option>
      `).join("");

      if (roomHotelSelect) roomHotelSelect.innerHTML = optionsHtml;
      if (availHotelSelect) availHotelSelect.innerHTML = optionsHtml;

      if (filterRoomHotel) {
        filterRoomHotel.innerHTML = `<option value="">All Hotels</option>` + optionsHtml;
      }
    }
  } catch (err) {
    console.error("Failed to load hotels dropdown:", err);
  }
}

// ==============================================================
// 4. ROOMS & INVENTORY MANAGEMENT
// ==============================================================
async function loadRoomsTable() {
  const tbody = document.getElementById("tbody-rooms");
  const filterHotel = document.getElementById("filter-room-hotel") ? document.getElementById("filter-room-hotel").value : "";
  if (!tbody) return;

  tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; padding: 20px;"><i class="fa-solid fa-circle-notch fa-spin"></i> Loading room inventory...</td></tr>`;

  try {
    const url = filterHotel ? `/api/rooms?hotel_id=${encodeURIComponent(filterHotel)}` : `/api/rooms`;
    const res = await fetch(url);
    const data = await res.json();

    if (data.success && data.rooms && data.rooms.length > 0) {
      tbody.innerHTML = data.rooms.map(r => `
        <tr>
          <td>
            <div style="font-weight: 700; color: var(--text-main);">${escapeHtml(r.name)}</div>
            <small style="color: var(--text-muted);">${escapeHtml(r.room_id)} • ${escapeHtml(r.category || 'Standard')}</small>
          </td>
          <td><small style="color: var(--text-muted);">${escapeHtml(r.hotel_name || r.hotel_id || 'Global')}</small></td>
          <td><strong style="color: var(--primary);">$${r.price_per_night}</strong></td>
          <td>${r.capacity_per_room || 2} Guests</td>
          <td>
            <div class="count-control">
              <button class="count-btn" title="Decrease room inventory" onclick="changeRoomCount('${r.room_id}', ${(r.total_rooms || 0) - 1}, '${r.hotel_id || ''}')">-</button>
              <span class="count-val" style="color: ${(r.total_rooms || 0) === 0 ? '#ef4444' : '#059669'};">${r.total_rooms || 0}</span>
              <button class="count-btn" title="Increase room inventory" onclick="changeRoomCount('${r.room_id}', ${(r.total_rooms || 0) + 1}, '${r.hotel_id || ''}')">+</button>
            </div>
            ${(r.total_rooms || 0) === 0 ? '<small style="color: #ef4444; display:block; margin-top:2px; font-weight:700;">Sold Out</small>' : ''}
          </td>
          <td>
            <button class="btn-delete-booking" onclick="deleteRoom('${r.room_id}', '${r.hotel_id || ''}')">
              <i class="fa-solid fa-trash"></i> Delete
            </button>
          </td>
        </tr>
      `).join("");
    } else {
      tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: #94a3b8; padding: 20px;">No rooms found. Add a room category above!</td></tr>`;
    }
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="6" style="color: #ef4444; text-align: center;">Failed to load room inventory.</td></tr>`;
  }
}

async function handleAddRoom(e) {
  e.preventDefault();
  const hotel_id = document.getElementById("room-hotel-select").value;
  const name = document.getElementById("room-name").value.trim();
  const category = document.getElementById("room-category").value;
  const price_per_night = parseFloat(document.getElementById("room-price").value) || 100;
  const capacity_per_room = parseInt(document.getElementById("room-capacity").value) || 2;
  const total_rooms = parseInt(document.getElementById("room-total").value) || 10;

  if (!hotel_id || !name) {
    alert("Please select hotel and provide room name.");
    return;
  }

  try {
    const res = await fetch("/api/rooms", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        hotel_id,
        name,
        category,
        price_per_night,
        capacity_per_room,
        total_rooms,
        available_rooms: total_rooms,
        description: `${category} room with luxurious appointments.`
      })
    });
    const result = await res.json();
    if (result.success) {
      document.getElementById("form-add-room").reset();
      await loadRoomsTable();
      await loadStats();
      alert(`Room category '${name}' saved successfully to MongoDB!`);
    } else {
      alert("Error adding room: " + (result.detail || result.message));
    }
  } catch (err) {
    alert("Request failed: " + err.message);
  }
}

async function changeRoomCount(roomId, newCount, hotelId) {
  if (newCount < 0) return;
  try {
    const res = await fetch("/api/rooms/update-count", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        room_id: roomId,
        new_count: newCount,
        hotel_id: hotelId || null
      })
    });
    const result = await res.json();
    if (result.success) {
      await loadRoomsTable();
      await loadStats();
    }
  } catch (err) {
    console.error("Failed to update room count:", err);
  }
}

async function deleteRoom(roomId, hotelId) {
  if (!confirm(`Delete room ${roomId}?`)) return;
  try {
    const url = hotelId ? `/api/rooms/${roomId}?hotel_id=${encodeURIComponent(hotelId)}` : `/api/rooms/${roomId}`;
    const res = await fetch(url, { method: "DELETE" });
    const result = await res.json();
    if (result.success) {
      await loadRoomsTable();
      await loadStats();
    }
  } catch (err) {
    alert("Failed to delete room: " + err.message);
  }
}

// ==============================================================
// 5. BOOKINGS LEDGER
// ==============================================================
async function loadBookingsTable() {
  const tbody = document.getElementById("tbody-bookings");
  if (!tbody) return;
  tbody.innerHTML = `<tr><td colspan="8" style="text-align:center; padding: 20px;"><i class="fa-solid fa-circle-notch fa-spin"></i> Loading bookings from MongoDB...</td></tr>`;

  try {
    const res = await fetch("/api/bookings");
    const data = await res.json();
    if (data.success && data.bookings && data.bookings.length > 0) {
      tbody.innerHTML = data.bookings.map(b => {
        let transferHtml = '<span class="badge-no">None</span>';
        if (b.airport_pickup && b.airport_drop) {
          transferHtml = '<span class="badge-yes"><i class="fa-solid fa-car-side"></i> Pick & Drop</span>';
        } else if (b.airport_pickup) {
          transferHtml = '<span class="badge-yes" style="background: #e0f2fe; color: #0284c7;"><i class="fa-solid fa-plane-arrival"></i> Pick-up</span>';
        } else if (b.airport_drop) {
          transferHtml = '<span class="badge-yes" style="background: #fef3c7; color: #d97706;"><i class="fa-solid fa-plane-departure"></i> Drop-off</span>';
        }

        return `
          <tr>
            <td><strong style="color: var(--primary);">${escapeHtml(b.booking_id)}</strong></td>
            <td>
              <div style="font-weight: 700; color: var(--text-main);">${escapeHtml(b.hotel_name || 'Grand Azure')}</div>
              <small style="color: var(--text-muted);">${escapeHtml(b.location_city || '')} (${escapeHtml(b.airport_code || '')})</small>
            </td>
            <td>
              <div style="font-weight: 600; color: var(--text-main);">${escapeHtml(b.guest_name)}</div>
              ${b.company_name ? `<small style="color: var(--text-muted);">${escapeHtml(b.company_name)}</small>` : ''}
            </td>
            <td>
              <div>${b.rooms_count}x ${escapeHtml(b.room_name)}</div>
              <small style="color: var(--text-muted);"><i class="fa-solid fa-utensils"></i> ${escapeHtml(b.food_preference || (b.food_included ? 'Food Included' : 'No Food'))}</small>
            </td>
            <td><small style="color: var(--text-muted);">${b.checkin_date} → ${b.checkout_date} (${b.total_nights}n)</small></td>
            <td>${transferHtml}</td>
            <td><strong style="color: var(--primary);">$${b.total_amount}</strong></td>
            <td><span class="status-tag confirmed">Confirmed</span></td>
            <td>
              <button class="btn-delete-booking" onclick="deleteBooking('${b.booking_id}')" title="Delete reservation">
                <i class="fa-solid fa-trash"></i> Delete
              </button>
            </td>
          </tr>
        `;
      }).join("");
    } else {
      tbody.innerHTML = `<tr><td colspan="9" style="text-align: center; color: #94a3b8; padding: 20px;">No bookings recorded yet in MongoDB.</td></tr>`;
    }
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="9" style="color: #ef4444; text-align: center;">Failed to load bookings ledger.</td></tr>`;
  }
}

async function deleteBooking(bookingId) {
  if (!confirm(`Are you sure you want to delete reservation ${bookingId}? This will remove it permanently from MongoDB.`)) return;
  try {
    const res = await fetch(`/api/bookings/${bookingId}`, { method: "DELETE" });
    const result = await res.json();
    if (result.success) {
      await loadBookingsTable();
      await loadStats();
      alert(`Reservation ${bookingId} has been successfully deleted from MongoDB.`);
    } else {
      alert("Failed to delete booking: " + (result.message || "Unknown error"));
    }
  } catch (err) {
    alert("Delete failed: " + err.message);
  }
}

// ==============================================================
// 6. DATE-SPECIFIC AVAILABILITY CALCULATOR
// ==============================================================
async function loadHotelAndRoomsForAvailability() {
  await loadHotelsDropdown();
}

async function testDateAvailability() {
  const hotel_id = document.getElementById("avail-hotel-select").value;
  const room_id = document.getElementById("avail-room-select").value;
  const checkin_date = document.getElementById("avail-cin").value;
  const checkout_date = document.getElementById("avail-cout").value;
  const requested_count = parseInt(document.getElementById("avail-rooms-needed").value) || 1;
  const resultBox = document.getElementById("avail-result-box");

  if (!checkin_date || !checkout_date) {
    resultBox.innerHTML = `<span style="color: #ef4444;">Please specify both Check-in and Check-out dates.</span>`;
    return;
  }

  if (checkout_date <= checkin_date) {
    resultBox.innerHTML = `<span style="color: #ef4444;">Check-out date must be after Check-in date.</span>`;
    return;
  }

  resultBox.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin"></i> Checking MongoDB reservation overlap...`;

  try {
    const res = await fetch("/api/rooms/check-availability", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        hotel_id,
        room_id,
        checkin_date,
        checkout_date,
        requested_count
      })
    });
    const data = await res.json();

    if (data.success) {
      if (data.is_available) {
        resultBox.innerHTML = `
          <span style="color: #10b981;">
            <i class="fa-solid fa-circle-check"></i> Available! ${data.remaining_rooms} room(s) remaining for these dates.
          </span>
        `;
      } else {
        resultBox.innerHTML = `
          <span style="color: #ef4444;">
            <i class="fa-solid fa-circle-xmark"></i> Unavailable (${data.remaining_rooms} available, ${requested_count} requested).
          </span>
        `;
      }
    } else {
      resultBox.innerHTML = `<span style="color: #ef4444;">Check failed: ${data.detail || data.message}</span>`;
    }
  } catch (err) {
    resultBox.innerHTML = `<span style="color: #ef4444;">Error checking availability: ${err.message}</span>`;
  }
}

// Helpers
function escapeHtml(text) {
  if (!text) return "";
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}
