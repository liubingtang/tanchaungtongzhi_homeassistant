/* State Popup frontend: subscribes to custom WS and shows styled popup */
(async () => {
  const conn = (await window.hassConnection).conn;

  function ensureContainer() {
    let wrap = document.querySelector("#state-popup-wrapper");
    if (!wrap) {
      wrap = document.createElement("div");
      wrap.id = "state-popup-wrapper";
      wrap.style.position = "fixed";
      wrap.style.inset = "0";
      wrap.style.pointerEvents = "none";
      wrap.style.display = "grid";
      wrap.style.placeItems = "center";
      wrap.style.zIndex = "2147483647"; // above HA headers
      document.body.appendChild(wrap);
    }
    return wrap;
  }

  function showPopup({ text, backgroundUrl, textColor, fontSize, textPosition }) {
    const wrap = ensureContainer();
    // Clear previous
    wrap.innerHTML = "";

    const card = document.createElement("div");
    card.style.width = "320px";
    card.style.maxWidth = "90vw";
    card.style.aspectRatio = "4 / 3";
    card.style.display = "flex";
    card.style.flexDirection = "column";
    card.style.justifyContent =
      textPosition === "top"
        ? "flex-start"
        : textPosition === "bottom"
        ? "flex-end"
        : "center";
    card.style.alignItems = "center";
    card.style.padding = "16px";
    card.style.boxSizing = "border-box";
    card.style.borderRadius = "18px";
    card.style.boxShadow = "0 16px 40px rgba(0,0,0,0.35)";
    card.style.background = backgroundUrl
      ? `center / cover no-repeat url("${backgroundUrl}")`
      : "linear-gradient(135deg, #0d47a1, #1976d2)";
    card.style.color = textColor || "#ffffff";
    card.style.fontSize = fontSize || "16px";
    card.style.fontWeight = "600";
    card.style.textAlign = "center";
    card.style.backdropFilter = "blur(4px)";
    card.style.pointerEvents = "auto";
    card.style.transition = "opacity 200ms ease, transform 200ms ease";
    card.style.opacity = "0";
    card.style.transform = "translateY(16px)";

    const label = document.createElement("div");
    label.textContent = text;
    label.style.textShadow = "0 2px 8px rgba(0,0,0,0.55)";
    label.style.wordBreak = "break-word";
    card.appendChild(label);

    wrap.appendChild(card);
    requestAnimationFrame(() => {
      card.style.opacity = "1";
      card.style.transform = "translateY(0)";
    });

    setTimeout(() => {
      card.style.opacity = "0";
      card.style.transform = "translateY(16px)";
      setTimeout(() => wrap.innerHTML = "", 220);
    }, 5000);
  }

  conn.subscribeMessage(
    (payload) => {
      const { entity_id, old, new: nv, friendly_name, last_changed, style = {} } =
        payload;
      const name = friendly_name || entity_id;
      const ts = last_changed
        ? new Date(last_changed).toLocaleTimeString()
        : "";
      const text = `${name}: ${old ?? "—"} → ${nv}${ts ? ` @ ${ts}` : ""}`;

      showPopup({
        text,
        backgroundUrl: style.background_url,
        textColor: style.text_color,
        fontSize: style.font_size,
        textPosition: style.text_position,
      });
    },
    { type: "state_popup/subscribe" }
  );
})();
