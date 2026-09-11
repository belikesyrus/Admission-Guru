/**
 * auth-state.js — Shared auth UI state management.
 * Reads JWT from localStorage and updates navbar links.
 * Works both when served via Flask (localhost:5000) and opened as file://.
 */

// Detect whether we're running via Flask or directly from the filesystem
const _isFileBased = location.protocol === "file:" || location.hostname === "";

// API base URL — always point to the Flask server
const API_BASE = _isFileBased ? "http://localhost:5000/api" : "/api";

// Root URL for redirects
const ROOT_URL = _isFileBased ? "http://localhost:5000/" : "/";

const AuthState = (() => {
  const KEY      = "ag_token";
  const USER_KEY = "ag_user";

  function getToken() {
    return localStorage.getItem(KEY);
  }

  function getUser() {
    try {
      return JSON.parse(localStorage.getItem(USER_KEY));
    } catch {
      return null;
    }
  }

  function setSession(token, user) {
    localStorage.setItem(KEY, token);
    localStorage.setItem(USER_KEY, JSON.stringify(user));
  }

  function clearSession() {
    localStorage.removeItem(KEY);
    localStorage.removeItem(USER_KEY);
  }

  function isLoggedIn() {
    return !!getToken();
  }

  function updateNavUI() {
    const authLinks    = document.getElementById("authLinks");
    const userMenu     = document.getElementById("userMenu");
    const dashLink     = document.getElementById("dashLink");
    const userGreeting = document.getElementById("userGreeting");

    if (!authLinks) return;

    if (isLoggedIn()) {
      const user = getUser();
      authLinks.style.display = "none";
      userMenu.style.display  = "flex";
      if (dashLink)     dashLink.style.display = "";
      if (userGreeting && user) {
        userGreeting.textContent = `Hi, ${user.name.split(" ")[0]} 👋`;
      }
    } else {
      authLinks.style.display = "flex";
      userMenu.style.display  = "none";
      if (dashLink) dashLink.style.display = "none";
    }
  }

  // Fetch wrapper that automatically adds the auth header
  async function authFetch(url, options = {}) {
    const token = getToken();
    const headers = {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers || {}),
    };
    return fetch(url, { ...options, headers });
  }

  // ── Init ────────────────────────────────────────────────────────────────
  document.addEventListener("DOMContentLoaded", () => {
    updateNavUI();

    // Navbar scroll shadow
    const navbar = document.getElementById("navbar");
    if (navbar) {
      window.addEventListener("scroll", () => {
        navbar.classList.toggle("scrolled", window.scrollY > 20);
      }, { passive: true });
    }

    // Mobile nav toggle
    const toggle   = document.getElementById("navToggle");
    const navLinks = document.getElementById("navLinks");
    if (toggle && navLinks) {
      toggle.addEventListener("click", () => {
        navLinks.classList.toggle("open");
      });
      // Close nav when a link is clicked
      navLinks.querySelectorAll("a").forEach(a => {
        a.addEventListener("click", () => navLinks.classList.remove("open"));
      });
    }

    // Logout button
    const logoutBtn = document.getElementById("logoutBtn");
    if (logoutBtn) {
      logoutBtn.addEventListener("click", () => {
        clearSession();
        window.location.href = ROOT_URL;
      });
    }
  });

  return {
    getToken,
    getUser,
    setSession,
    clearSession,
    isLoggedIn,
    authFetch,
    updateNavUI,
    API_BASE,
  };
})();
