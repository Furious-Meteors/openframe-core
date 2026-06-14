/* ==========================================================================
   FlamAI Docs — Custom JavaScript
   All features use document$.subscribe() for Material instant navigation.
   ========================================================================== */

document$.subscribe(function () {

  /* ── 1. Reading Progress Bar ─────────────────────────────────────────── */

  (function initProgressBar() {
    // Create bar if it doesn't exist yet
    var bar = document.getElementById("fl-progress-bar");
    if (!bar) {
      bar = document.createElement("div");
      bar.id = "fl-progress-bar";
      bar.style.cssText = [
        "position: fixed",
        "top: 0",
        "left: 0",
        "height: 3px",
        "width: 0%",
        "background: linear-gradient(90deg, #4E8A2A, #8CC63F)",
        "z-index: 9999",
        "transition: width 0.1s linear",
        "pointer-events: none",
      ].join(";");
      document.body.appendChild(bar);
    }

    function updateProgress() {
      var scrollTop  = window.scrollY || document.documentElement.scrollTop;
      var docHeight  = document.documentElement.scrollHeight - window.innerHeight;
      var progress   = docHeight > 0 ? (scrollTop / docHeight) * 100 : 0;
      bar.style.width = Math.min(progress, 100) + "%";
    }

    // Remove old listener before adding new one (instant navigation safe)
    window.removeEventListener("scroll", updateProgress);
    window.addEventListener("scroll", updateProgress, { passive: true });

    // Reset to 0 on page load
    bar.style.width = "0%";
  })();


  /* ── 2. Anchor Copy on Heading Hover ─────────────────────────────────── */

  (function initAnchorCopy() {
    var headings = document.querySelectorAll(
      ".md-content h1[id], .md-content h2[id], .md-content h3[id], .md-content h4[id]"
    );

    headings.forEach(function (heading) {
      // Don't add twice
      if (heading.querySelector(".fl-anchor-btn")) return;

      var btn = document.createElement("button");
      btn.className    = "fl-anchor-btn";
      btn.title        = "Copy link";
      btn.style.cssText = [
        "display: inline-flex",
        "align-items: center",
        "justify-content: center",
        "margin-left: 0.4em",
        "padding: 0.1em 0.3em",
        "background: none",
        "border: none",
        "border-radius: 4px",
        "cursor: pointer",
        "opacity: 0",
        "transition: opacity 0.15s",
        "vertical-align: middle",
        "color: #6DB33F",
        "font-size: 0.75em",
      ].join(";");

      // Link icon (SVG)
      btn.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>';

      heading.appendChild(btn);

      // Show/hide on heading hover
      heading.addEventListener("mouseenter", function () {
        btn.style.opacity = "1";
      });
      heading.addEventListener("mouseleave", function () {
        if (!btn.classList.contains("fl-anchor-copied")) {
          btn.style.opacity = "0";
        }
      });

      // Copy URL on click
      btn.addEventListener("click", function (e) {
        e.preventDefault();
        e.stopPropagation();

        var url = window.location.origin
          + window.location.pathname
          + "#"
          + heading.id;

        navigator.clipboard.writeText(url).then(function () {
          // Swap to checkmark
          btn.classList.add("fl-anchor-copied");
          btn.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#8CC63F" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>';
          btn.style.opacity = "1";

          // Reset after 2s
          setTimeout(function () {
            btn.classList.remove("fl-anchor-copied");
            btn.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>';
            btn.style.opacity = "0";
          }, 2000);
        }).catch(function () {
          // Fallback for browsers without clipboard API
          var temp = document.createElement("textarea");
          temp.value = url;
          document.body.appendChild(temp);
          temp.select();
          document.execCommand("copy");
          document.body.removeChild(temp);
        });
      });
    });
  })();


  /* ── 3. Active Sidebar Section Highlight ─────────────────────────────── */

  (function initSidebarHighlight() {
    // Only run on desktop where left sidebar is visible
    var sidebar = document.querySelector(".md-sidebar--primary .md-nav--primary");
    if (!sidebar) return;

    var headings = Array.from(
      document.querySelectorAll(".md-content h2[id], .md-content h3[id]")
    );
    if (headings.length === 0) return;

    var activeLink = null;

    function setActive(id) {
      // Remove previous active highlight
      if (activeLink) {
        activeLink.classList.remove("fl-sidebar-active");
        activeLink.style.removeProperty("color");
        activeLink.style.removeProperty("font-weight");
      }

      if (!id) return;

      // Find the nav link matching this heading id
      var link = sidebar.querySelector('a[href="#' + id + '"]');
      if (!link) {
        // Try matching against full path
        var path = window.location.pathname;
        link = sidebar.querySelector('a[href="' + path + '#' + id + '"]');
      }

      if (link) {
        link.classList.add("fl-sidebar-active");
        link.style.color      = "#6DB33F";
        link.style.fontWeight = "600";
        activeLink = link;
      }
    }

    // IntersectionObserver — track which heading is near the top
    var observer = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            setActive(entry.target.id);
          }
        });
      },
      {
        rootMargin: "-10% 0px -80% 0px",
        threshold: 0,
      }
    );

    headings.forEach(function (h) { observer.observe(h); });

    // Disconnect old observer on next navigation
    document$.subscribe(function () { observer.disconnect(); });
  })();

});
