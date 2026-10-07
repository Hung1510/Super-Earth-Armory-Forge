/* Super Earth Armory Forge web builder - the page mascot.
   A vanilla JS port of page-mascot's component by Kamran Ahmed (MIT, see mascot/LICENSE-page-mascot.txt;
   https://github.com/nilbuild/page-mascot): the head follows the cursor in eight directions with a dead
   zone and hysteresis, a click blinks it and sets off a heart / sparkle / grin, four quick clicks make it
   dizzy. The two 3x3 sprite sheets are the "astronaut" character from that repo, resized.
   "Hide the mascot" in the footer turns it off (remembered in this browser only). */
(function () {
  "use strict";
  const DIRECTIONS = ["up-left", "up", "up-right", "left", "center", "right", "down-left", "down", "down-right"];
  const REACTIONS = ["blink", "heart", "sparkle", "surprised", "wink", "bashful", "sleepy", "dizzy", "delighted"];
  const CLOCKWISE = ["right", "down-right", "down", "down-left", "left", "up-left", "up", "up-right"];
  const SECTOR = (Math.PI * 2) / CLOCKWISE.length, HYSTERESIS = 0.12, DEAD_ZONE = 70;
  const PAYOFFS = ["heart", "sparkle", "delighted"];
  const BOOP_PAYOFF = 120, BOOP_END = 560, SQUASH_MS = 420, DIZZY_AFTER = 4, DIZZY_WINDOW = 1600, DIZZY_END = 1100;
  const SQUASH = [
    { transform: "scale(1, 1)", easing: "ease-in" },
    { transform: "scale(1.10, 0.86)", offset: 0.18, easing: "ease-out" },
    { transform: "scale(0.95, 1.08)", offset: 0.45, easing: "ease-in-out" },
    { transform: "scale(1.03, 0.97)", offset: 0.72, easing: "ease-in-out" },
    { transform: "scale(1, 1)" },
  ];
  const wrap = (a) => Math.atan2(Math.sin(a), Math.cos(a));
  const cell = (i) => `${(i % 3) * 50}% ${Math.floor(i / 3) * 50}%`;
  const KEY = "armoryForgeMascot";
  const store = {
    get() { try { return localStorage.getItem(KEY); } catch (e) { return null; } },
    set(v) { try { localStorage.setItem(KEY, v); } catch (e) { /* private window: just for this visit */ } },
  };

  let button = null, squash = null, dirLayer = null, reactLayer = null;
  let timers = [], boops = { count: 0, at: 0 }, sector = -1, pointer = null;
  const reduceMotion = () => window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function layer(url) {
    const el = document.createElement("span");
    el.style.cssText = "position:absolute;inset:0;background-size:300% 300%;background-repeat:no-repeat;background-image:url(" + url + ")";
    return el;
  }
  function setDirection(d) { dirLayer.style.backgroundPosition = cell(DIRECTIONS.indexOf(d)); }
  function setReaction(r) {
    reactLayer.style.backgroundPosition = cell(REACTIONS.indexOf(r || "blink"));
    reactLayer.style.opacity = r ? "1" : "0";
    dirLayer.style.opacity = r ? "0" : "1";
  }
  function aim() {
    if (!button || !pointer) return;
    const box = button.getBoundingClientRect();
    const dx = pointer.x - (box.left + box.width / 2), dy = pointer.y - (box.top + box.height / 2);
    if (Math.hypot(dx, dy) < DEAD_ZONE) { sector = -1; setDirection("center"); return; }
    const angle = Math.atan2(dy, dx);
    if (sector !== -1 && Math.abs(wrap(angle - sector * SECTOR)) < SECTOR / 2 + HYSTERESIS) return;
    sector = (Math.round(angle / SECTOR) + CLOCKWISE.length) % CLOCKWISE.length;
    setDirection(CLOCKWISE[sector]);
  }
  function boop() {
    timers.forEach(clearTimeout);
    timers = [];
    const later = (ms, next) => timers.push(setTimeout(() => setReaction(next), ms));
    const now = Date.now();
    boops.count = now - boops.at < DIZZY_WINDOW ? boops.count + 1 : 1;
    boops.at = now;
    if (boops.count >= DIZZY_AFTER) {
      boops.count = 0;
      setReaction("dizzy");
      later(DIZZY_END, null);
    } else {
      setReaction("blink");
      later(BOOP_PAYOFF, PAYOFFS[(boops.count - 1) % PAYOFFS.length]);
      later(BOOP_END, null);
    }
    if (!reduceMotion() && squash.animate) squash.animate(SQUASH, { duration: SQUASH_MS, easing: "linear" });
  }

  function show() {
    if (button) return;
    button = document.createElement("button");
    button.type = "button";
    button.id = "pageMascot";
    button.setAttribute("aria-label", "Boop the mascot");
    button.style.cssText = "position:fixed;right:14px;bottom:14px;z-index:30;width:96px;height:96px;padding:0;border:0;" +
      "background:transparent;appearance:none;cursor:pointer;user-select:none;-webkit-tap-highlight-color:transparent";
    squash = document.createElement("span");
    squash.style.cssText = "position:relative;display:block;width:100%;height:100%;transform-origin:50% 78%";
    dirLayer = layer("mascot/astronaut-directions.webp");
    reactLayer = layer("mascot/astronaut-reactions.webp");     // always mounted: fetched up front, not on the first click
    squash.append(dirLayer, reactLayer);
    button.append(squash);
    button.addEventListener("click", boop);
    setDirection("center");
    setReaction(null);
    document.body.append(button);
    if (window.matchMedia && window.matchMedia("(hover: hover) and (pointer: fine)").matches) {
      window.addEventListener("pointermove", onMove, { passive: true });
      window.addEventListener("scroll", aim, { passive: true });
    }
  }
  function onMove(e) { pointer = { x: e.clientX, y: e.clientY }; aim(); }
  function hide() {
    if (!button) return;
    timers.forEach(clearTimeout);
    timers = [];
    window.removeEventListener("pointermove", onMove);
    window.removeEventListener("scroll", aim);
    button.remove();
    button = squash = dirLayer = reactLayer = null;
    sector = -1;
  }
  function sync() {
    const link = document.getElementById("mascotToggle");
    if (link) link.textContent = button ? "hide the mascot" : "show the mascot";
  }
  function start() {
    if (store.get() !== "off") show();
    const link = document.getElementById("mascotToggle");
    if (link) {
      link.addEventListener("click", (e) => {
        e.preventDefault();
        if (button) { hide(); store.set("off"); } else { show(); store.set("on"); }
        sync();
      });
    }
    sync();
  }
  window.AFMascot = { show, hide };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start); else start();
})();
