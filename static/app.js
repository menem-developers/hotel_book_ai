// ==========================================================================
// NORTHSTAR AIR SERVICE - CONVERSATIONAL AGENT JAVASCRIPT
// Handles in-chat interactive cards, typo clarifications, and dummy attachment
// ==========================================================================

let currentSessionId = localStorage.getItem("northstar_session_id") || null;
let lastState = null;
let cachedBookings = [];

// DOM Elements
const chatCanvas = document.getElementById("chat-canvas");
const chatMessages = document.getElementById("chat-messages");
const chatForm = document.getElementById("chat-form");
const chatInput = document.getElementById("chat-input");
const btnSend = document.getElementById("btn-send");
const typingIndicator = document.getElementById("typing-indicator");

// Sidebar Nav Elements
const btnNewChat = document.getElementById("btn-new-chat");
const navServiceDesk = document.getElementById("nav-service-desk");
const navBookingsLedger = document.getElementById("nav-bookings-ledger");
const cardTryBooking = document.getElementById("card-try-booking");
const btnAttachDummy = document.getElementById("btn-attach-dummy");

// Bookings Ledger Modal Elements
const bookingsModal = document.getElementById("bookings-modal");
const btnCloseModal = document.getElementById("btn-close-modal");
const bookingsTableContainer = document.getElementById("bookings-table-container");
const ledgerSearchInput = document.getElementById("ledger-search-input");
const toastContainer = document.getElementById("toast-container");

// Initialize on Load
document.addEventListener("DOMContentLoaded", async () => {
  await initializeChat();

  // Attach Event Listeners
  chatForm.addEventListener("submit", handleSendMessage);
  btnNewChat.addEventListener("click", handleResetChat);
  navBookingsLedger.addEventListener("click", openBookingsModal);
  btnCloseModal.addEventListener("click", () => bookingsModal.classList.remove("open"));
  
  // Close modal when clicking outside
  bookingsModal.addEventListener("click", (e) => {
    if (e.target === bookingsModal) bookingsModal.classList.remove("open");
  });

  // Dummy attachment handler
  if (btnAttachDummy) {
    btnAttachDummy.addEventListener("click", () => {
      showToast("Attachment option is a demo dummy feature. Please type your details in chat.");
    });
  }

  // Try an existing booking sample card
  if (cardTryBooking) {
    cardTryBooking.addEventListener("click", () => {
      chatInput.value = "What is my booking details?";
      chatForm.dispatchEvent(new Event("submit"));
    });
  }

  // Input changes toggle send button state
  chatInput.addEventListener("input", () => {
    if (chatInput.value.trim().length > 0) {
      btnSend.classList.add("active");
    } else {
      btnSend.classList.remove("active");
    }
  });

  // Support Enter to submit (Shift+Enter for new line)
  chatInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      chatForm.dispatchEvent(new Event("submit"));
    }
  });

  // Live filter for bookings ledger
  if (ledgerSearchInput) {
    ledgerSearchInput.addEventListener("input", filterBookingsTable);
  }
});

// ==========================================================================
// CHAT INITIALIZATION & MESSAGING
// ==========================================================================

async function initializeChat() {
  try {
    const res = await fetch("/api/chat/init", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: currentSessionId })
    });
    const data = await res.json();
    currentSessionId = data.session_id;
    localStorage.setItem("northstar_session_id", currentSessionId);
    lastState = data.state;

    // Clear canvas
    chatMessages.innerHTML = "";
    // Only append if session has existing messages; otherwise start completely empty until user says hi!
    if (data.reply && data.reply.trim().length > 0) {
      appendAssistantBubble(data.reply, data.options, data.quick_replies);
    }
  } catch (err) {
    console.error("Init chat error:", err);
    chatMessages.innerHTML = "";
  }
}

async function handleSendMessage(e) {
  if (e) e.preventDefault();
  const text = chatInput.value.trim();
  if (!text) return;

  // Append user message bubble
  appendUserBubble(text);
  chatInput.value = "";
  chatInput.style.height = "auto";
  btnSend.classList.remove("active");
  chatInput.disabled = true;
  btnSend.disabled = true;

  // Show typing indicator
  showTyping(true);

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: currentSessionId,
        message: text
      })
    });

    if (!res.ok) throw new Error("Failed to send message");
    const data = await res.json();

    currentSessionId = data.session_id;
    localStorage.setItem("northstar_session_id", currentSessionId);
    lastState = data.state;

    showTyping(false);
    appendAssistantBubble(data.reply, data.options, data.quick_replies, data.booking);
  } catch (err) {
    showTyping(false);
    appendAssistantBubble("Apologies, I encountered a brief network delay. Please try again or rephrase your answer.");
    console.error("Chat error:", err);
  } finally {
    chatInput.disabled = false;
    btnSend.disabled = false;
    chatInput.focus();
    scrollToBottom();
  }
}

async function handleResetChat() {
  try {
    const res = await fetch("/api/chat/reset", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: currentSessionId })
    });
    const data = await res.json();
    currentSessionId = data.session_id;
    localStorage.setItem("northstar_session_id", currentSessionId);
    lastState = data.state;

    // Reset starts completely empty until user sends a greeting
    chatMessages.innerHTML = "";
    if (data.reply && data.reply.trim().length > 0) {
      appendAssistantBubble(data.reply, data.options, data.quick_replies);
    }
    showToast("Conversation cleared. Say 'Hi' to begin.");
  } catch (err) {
    console.error("Reset error:", err);
    chatMessages.innerHTML = "";
  }
}

// ==========================================================================
// MESSAGE BUBBLE RENDERING WITH IN-CHAT OPTION CARDS
// ==========================================================================

function appendUserBubble(text) {
  const row = document.createElement("div");
  row.className = "user-message-row";
  row.innerHTML = `
    <div class="message-bubble user-bubble">
      ${escapeHtml(text)}
    </div>
    <div class="user-avatar">
      <i class="fa-solid fa-user"></i>
    </div>
  `;
  chatMessages.appendChild(row);
  scrollToBottom();
}

function appendAssistantBubble(text, options = null, quickReplies = [], booking = null) {
  const row = document.createElement("div");
  row.className = "assistant-message-row";

  let optionsHtml = "";
  if (options) {
    optionsHtml = renderInChatOptions(options);
  }

  let quickRepliesHtml = "";
  if (quickReplies && quickReplies.length > 0) {
    quickRepliesHtml = `
      <div class="inchat-quick-replies">
        ${quickReplies.map(qr => `
          <button type="button" class="inchat-reply-chip" onclick="handleQuickSelect('${escapeHtml(qr)}')">
            ${escapeHtml(qr)}
          </button>
        `).join("")}
      </div>
    `;
  }

  let voucherHtml = "";
  if (booking) {
    voucherHtml = renderVoucherCard(booking);
  }

  row.innerHTML = `
    <div class="assistant-avatar">
      <i class="fa-solid fa-robot"></i>
    </div>
    <div class="bubble-wrapper">
      <div class="assistant-header-line">
        <span class="assistant-name">Northstar Assistant</span>
        <span class="assistant-tag">AI</span>
      </div>
      <div class="message-bubble assistant-bubble">
        ${formatMarkdown(text)}
        ${voucherHtml}
        ${optionsHtml}
        ${quickRepliesHtml}
      </div>
    </div>
  `;

  chatMessages.appendChild(row);
  scrollToBottom();
}

// Render Interactive Option Cards directly inside Assistant message
function renderInChatOptions(options) {
  if (!options || !options.type) return "";

  // 1. Destination Cards
  if (options.type === "locations" && options.items) {
    return `
      <div class="in-chat-options-container">
        <div class="options-title-bar">
          <i class="fa-solid fa-plane-arrival"></i> Available Arrival Airport Hubs:
        </div>
        <div class="destinations-grid">
          ${options.items.map(loc => `
            <div class="inchat-dest-card" onclick="handleQuickSelect('${escapeHtml(loc.city)}')">
              <div class="inchat-dest-badge">
                <i class="fa-solid fa-plane-arrival"></i>
                <span>${escapeHtml(loc.airport_code)}</span>
              </div>
              <div class="inchat-dest-info">
                <span class="inchat-dest-city">${escapeHtml(loc.city)}</span>
                <span class="inchat-dest-airport">${escapeHtml(loc.airport_name)}</span>
              </div>
            </div>
          `).join("")}
        </div>
      </div>
    `;
  }

  // 2. Hotel Cards
  if (options.type === "hotels" && options.items) {
    return `
      <div class="in-chat-options-container">
        <div class="options-title-bar">
          <i class="fa-solid fa-hotel"></i> Available Properties in ${escapeHtml(options.location_city || 'City')}:
        </div>
        <div class="hotels-cards-list">
          ${options.items.map(h => `
            <div class="inchat-hotel-card" onclick="handleQuickSelect('${escapeHtml(h.name)}')">
              <img src="${h.image_url || 'https://images.unsplash.com/photo-1566073771259-6a8506099945?auto=format&fit=crop&w=600&q=80'}" alt="${escapeHtml(h.name)}" class="inchat-hotel-img" loading="lazy">
              <div class="inchat-hotel-details">
                <div class="inchat-hotel-header">
                  <span class="inchat-hotel-name">${escapeHtml(h.name)}</span>
                  <span class="inchat-hotel-rating">⭐ ${h.rating || 4.8}</span>
                </div>
                <span class="inchat-hotel-address"><i class="fa-solid fa-location-dot"></i> ${escapeHtml(h.address)}</span>
                <p class="inchat-hotel-desc">${escapeHtml(h.description || '')}</p>
                <div class="inchat-hotel-footer">
                  <span class="inchat-btn-select">Select this hotel <i class="fa-solid fa-arrow-right"></i></span>
                </div>
              </div>
            </div>
          `).join("")}
        </div>
      </div>
    `;
  }

  // 3. Room Type Cards (extra details omitted - only clickable options rendered via quick replies)
  if (options.type === "rooms") {
    return "";
  }

  // Food & Dining Option Cards
  if (options.type === "food" && options.items) {
    return `
      <div class="in-chat-options-container">
        <div class="options-title-bar">
          <i class="fa-solid fa-utensils"></i> Food & Dining Preference:
        </div>
        <div class="vehicles-grid">
          ${options.items.map(f => `
            <div class="inchat-vehicle-card" onclick="handleQuickSelect('${escapeHtml(f.title)}')">
              <div class="vehicle-header-row">
                <span class="vehicle-title">${escapeHtml(f.title)}</span>
                <span class="vehicle-badge">${escapeHtml(f.badge || '')}</span>
              </div>
              <p class="vehicle-desc">${escapeHtml(f.desc || '')}</p>
            </div>
          `).join("")}
        </div>
      </div>
    `;
  }

  // 4. Vehicle Transfer Option Cards
  if (options.type === "vehicles" && options.items) {
    return `
      <div class="in-chat-options-container">
        <div class="options-title-bar">
          <i class="fa-solid fa-car-side"></i> Airport Transportation Options:
        </div>
        <div class="vehicles-grid">
          ${options.items.map(v => `
            <div class="inchat-vehicle-card" onclick="handleQuickSelect('${escapeHtml(v.title)}')">
              <div class="vehicle-header-row">
                <span class="vehicle-title">${escapeHtml(v.title)}</span>
                <span class="vehicle-badge">${escapeHtml(v.badge || '')}</span>
              </div>
              <p class="vehicle-desc">${escapeHtml(v.desc || '')}</p>
            </div>
          `).join("")}
        </div>
      </div>
    `;
  }

  // 5. Typo Clarification Card ("Did you mean Chennai? Is Chennai right?")
  if (options.type === "clarification") {
    return `
      <div class="in-chat-options-container">
        <div class="inchat-clarify-card">
          <span class="clarify-text">
            <i class="fa-solid fa-circle-question"></i> ${escapeHtml(options.title || 'Did you mean this?')}
          </span>
          <div class="clarify-actions">
            <button type="button" class="btn-clarify-yes" onclick="handleQuickSelect('${escapeHtml(options.confirm_value || options.confirm_text)}')">
              ${escapeHtml(options.confirm_text || 'Yes, correct')}
            </button>
            <button type="button" class="btn-clarify-no" onclick="handleQuickSelect('${escapeHtml(options.cancel_text || 'No, choose another')}')">
              ${escapeHtml(options.cancel_text || 'No')}
            </button>
          </div>
        </div>
      </div>
    `;
  }

  // 6. Confirmation Options
  if (options.type === "confirmation" && options.items) {
    return `
      <div class="in-chat-options-container">
        <div class="inchat-clarify-card" style="display: flex; gap: 10px; justify-content: flex-start; padding: 10px 14px; background: transparent; border: none;">
          ${options.items.map(it => `
            <button type="button" class="${it.primary ? 'btn-clarify-yes' : 'btn-clarify-no'}" onclick="handleQuickSelect('${escapeHtml(it.label)}')">
              ${escapeHtml(it.label)}
            </button>
          `).join("")}
        </div>
      </div>
    `;
  }

  return "";
}

// Render Confirmed Booking Voucher Card
function renderVoucherCard(b) {
  const pickup = b.airport_pickup ? "✅ Yes (Arrival)" : "❌ No";
  const drop = b.airport_drop ? "✅ Yes (Departure)" : "❌ No";
  return `
    <div class="inchat-voucher-card">
      <div class="voucher-header">
        <span class="voucher-brand"><i class="fa-solid fa-plane-up"></i> NORTHSTAR AIR SERVICE</span>
        <span class="voucher-tag">CONFIRMED • ${b.booking_id}</span>
      </div>
      <div class="voucher-details-grid">
        <div class="voucher-row">
          <span class="voucher-label">Property</span>
          <span class="voucher-val">${escapeHtml(b.hotel_name || 'Grand Azure')}</span>
        </div>
        <div class="voucher-row">
          <span class="voucher-label">Destination</span>
          <span class="voucher-val">${escapeHtml(b.location_city || 'City')} (${escapeHtml(b.airport_code || 'Hub')})</span>
        </div>
        <div class="voucher-row">
          <span class="voucher-label">Guest / Org</span>
          <span class="voucher-val">${escapeHtml(b.guest_name || 'Guest')}</span>
        </div>
        <div class="voucher-row">
          <span class="voucher-label">Rooms</span>
          <span class="voucher-val">${b.rooms_count || 1} x ${escapeHtml(b.room_name || 'Room')}</span>
        </div>
        <div class="voucher-row">
          <span class="voucher-label">Dates</span>
          <span class="voucher-val">${b.checkin_date} to ${b.checkout_date}</span>
        </div>
        <div class="voucher-row">
          <span class="voucher-label">Total Amount</span>
          <span class="voucher-val" style="color: #0d9488; font-size: 14px; font-weight: 800;">$${b.total_amount}</span>
        </div>
        <div class="voucher-row">
          <span class="voucher-label">Food / Dining</span>
          <span class="voucher-val">${escapeHtml(b.food_preference || (b.food_included ? 'Yes, Food Included' : 'No Food (Room Only)'))}</span>
        </div>
        <div class="voucher-row">
          <span class="voucher-label">Airport Pick-up</span>
          <span class="voucher-val">${pickup}</span>
        </div>
        <div class="voucher-row">
          <span class="voucher-label">Airport Drop-off</span>
          <span class="voucher-val">${drop}</span>
        </div>
      </div>
    </div>
  `;
}

// Global click handler for in-chat cards and quick reply chips
window.handleQuickSelect = function(text) {
  chatInput.value = text;
  chatForm.dispatchEvent(new Event("submit"));
};

// ==========================================================================
// BOOKINGS LEDGER MODAL MANAGEMENT
// ==========================================================================

async function openBookingsModal() {
  bookingsModal.classList.add("open");
  bookingsTableContainer.innerHTML = `
    <div style="text-align: center; padding: 24px; color: #64748b;">
      <i class="fa-solid fa-spinner fa-spin" style="font-size: 20px; color: #0d9488;"></i>
      <p style="margin-top: 8px;">Loading reservations from MongoDB...</p>
    </div>
  `;

  try {
    const res = await fetch("/api/bookings");
    if (!res.ok) throw new Error("Failed to fetch bookings");
    const data = await res.json();
    cachedBookings = data.bookings || [];
    renderBookingsTable(cachedBookings);
  } catch (err) {
    bookingsTableContainer.innerHTML = `
      <div style="text-align: center; padding: 20px; color: #ef4444;">
        Failed to load bookings ledger.
      </div>
    `;
  }
}

function renderBookingsTable(bookings) {
  if (bookings.length === 0) {
    bookingsTableContainer.innerHTML = `
      <div style="text-align: center; padding: 30px; color: #94a3b8;">
        <i class="fa-regular fa-folder-open" style="font-size: 28px; margin-bottom: 8px;"></i>
        <p>No bookings currently recorded in MongoDB.</p>
      </div>
    `;
    return;
  }

  bookingsTableContainer.innerHTML = `
    <table class="ledger-table">
      <thead>
        <tr>
          <th>Reference</th>
          <th>Guest / Org</th>
          <th>Hotel & Hub</th>
          <th>Dates</th>
          <th>Rooms</th>
          <th>Vehicle</th>
          <th>Total</th>
          <th>Action</th>
        </tr>
      </thead>
      <tbody>
        ${bookings.map(b => {
          const v = (b.airport_pickup && b.airport_drop) ? "Both" : (b.airport_pickup ? "Pick-up" : (b.airport_drop ? "Drop-off" : "None"));
          return `
            <tr id="booking-row-${b.booking_id}">
              <td><strong style="color: #0d9488;">${b.booking_id}</strong></td>
              <td>
                <div style="font-weight: 600;">${escapeHtml(b.guest_name || 'Guest')}</div>
                <div style="font-size: 10px; color: #94a3b8;">${escapeHtml(b.contact_email || b.contact_phone || '')}</div>
              </td>
              <td>
                <div style="font-weight: 600;">${escapeHtml(b.hotel_name || 'Grand Azure')}</div>
                <div style="font-size: 10px; color: #94a3b8;">${escapeHtml(b.location_city || '')} (${escapeHtml(b.airport_code || '')})</div>
              </td>
              <td>${b.checkin_date} to ${b.checkout_date}</td>
              <td>
                <div>${b.rooms_count} x ${escapeHtml(b.room_name || 'Room')}</div>
                <div style="font-size: 10px; color: #64748b; margin-top: 2px;"><i class="fa-solid fa-utensils"></i> ${escapeHtml(b.food_preference || (b.food_included ? 'Food Included' : 'No Food'))}</div>
              </td>
              <td><span class="status-tag confirmed">${v}</span></td>
              <td><strong>$${b.total_amount}</strong></td>
              <td>
                <button type="button" class="btn-delete-booking" onclick="deleteBookingEntry('${b.booking_id}')">
                  <i class="fa-solid fa-trash-can"></i> Delete
                </button>
              </td>
            </tr>
          `;
        }).join("")}
      </tbody>
    </table>
  `;
}

function filterBookingsTable() {
  const query = ledgerSearchInput.value.toLowerCase().trim();
  if (!query) {
    renderBookingsTable(cachedBookings);
    return;
  }
  const filtered = cachedBookings.filter(b => {
    return (
      (b.booking_id && b.booking_id.toLowerCase().includes(query)) ||
      (b.guest_name && b.guest_name.toLowerCase().includes(query)) ||
      (b.hotel_name && b.hotel_name.toLowerCase().includes(query)) ||
      (b.location_city && b.location_city.toLowerCase().includes(query)) ||
      (b.contact_email && b.contact_email.toLowerCase().includes(query))
    );
  });
  renderBookingsTable(filtered);
}

window.deleteBookingEntry = async function(bookingId) {
  if (!confirm(`Are you sure you want to permanently delete reservation ${bookingId}?`)) {
    return;
  }

  try {
    const res = await fetch(`/api/bookings/${bookingId}`, {
      method: "DELETE"
    });
    if (!res.ok) throw new Error("Delete failed");

    cachedBookings = cachedBookings.filter(b => b.booking_id !== bookingId);
    filterBookingsTable();
    showToast(`Booking ${bookingId} deleted successfully.`);
  } catch (err) {
    showToast("Failed to delete booking.");
  }
};

// ==========================================================================
// UTILITY HELPERS
// ==========================================================================

function showTyping(show) {
  if (typingIndicator) {
    typingIndicator.style.display = show ? "flex" : "none";
    if (show) scrollToBottom();
  }
}

function scrollToBottom() {
  if (chatCanvas) {
    setTimeout(() => {
      chatCanvas.scrollTop = chatCanvas.scrollHeight;
    }, 50);
  }
}

function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function formatMarkdown(text) {
  if (!text) return "";
  let html = escapeHtml(text);

  // Bold **text**
  html = html.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");

  // Inline code `code`
  html = html.replace(/`([^`]+)`/g, "<code style='background: #f1f5f9; padding: 2px 4px; border-radius: 4px; font-size: 12px;'>$1</code>");

  // Lists: • or -
  html = html.replace(/^[•\-\*]\s+(.*)$/gm, "<li>$1</li>");
  html = html.replace(/(<li>.*<\/li>)/s, "<ul style='margin: 6px 0 6px 18px;'>$1</ul>");

  // Paragraph breaks
  html = html.replace(/\n\n+/g, "</p><p>");
  html = html.replace(/\n/g, "<br>");

  return `<p>${html}</p>`;
}

function showToast(message) {
  if (!toastContainer) return;
  const t = document.createElement("div");
  t.className = "toast";
  t.textContent = message;
  toastContainer.appendChild(t);
  setTimeout(() => {
    t.style.opacity = "0";
    setTimeout(() => t.remove(), 250);
  }, 2800);
}
