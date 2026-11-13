(function () {
  function initSidebar() {
    var toggle = document.querySelector("[data-sidebar-toggle]");
    var backdrop = document.querySelector("[data-sidebar-close]");
    var collapse = document.querySelector("[data-sidebar-collapse]");

    function closeSidebar() {
      document.body.classList.remove("sidebar-open");
      if (toggle) toggle.setAttribute("aria-label", "Open menu");
    }

    if (toggle) {
      toggle.addEventListener("click", function () {
        var open = document.body.classList.toggle("sidebar-open");
        toggle.setAttribute("aria-label", open ? "Close menu" : "Open menu");
      });
    }
    if (backdrop) backdrop.addEventListener("click", closeSidebar);
    if (collapse) {
      collapse.addEventListener("click", function () {
        document.body.classList.toggle("sidebar-collapsed");
      });
    }
    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape") closeSidebar();
    });
    window.addEventListener("resize", function () {
      if (window.innerWidth > 900) closeSidebar();
    });
  }

  function initUserMenu() {
    var button = document.querySelector("[data-user-toggle]");
    var menu = document.querySelector("[data-user-menu]");
    if (!button || !menu) return;

    button.addEventListener("click", function () {
      var open = menu.hasAttribute("hidden");
      if (open) menu.removeAttribute("hidden");
      else menu.setAttribute("hidden", "");
      button.setAttribute("aria-expanded", open ? "true" : "false");
    });

    document.addEventListener("click", function (event) {
      if (!button.contains(event.target) && !menu.contains(event.target)) {
        menu.setAttribute("hidden", "");
        button.setAttribute("aria-expanded", "false");
      }
    });
  }

  function initGreeting() {
    var el = document.querySelector("[data-daypart]");
    if (!el) return;
    var hour = new Date().getHours();
    el.textContent = hour < 12 ? "Morning" : hour < 17 ? "Afternoon" : "Evening";
  }

  function animateCounters() {
    var nodes = document.querySelectorAll("[data-count]");
    nodes.forEach(function (node) {
      var target = Number(node.getAttribute("data-count"));
      if (!Number.isFinite(target)) return;
      node.textContent = String(target);
    });
  }

  function bindTableFilter(options) {
    var rows = Array.prototype.slice.call(document.querySelectorAll(options.rowSelector));
    var chips = Array.prototype.slice.call(document.querySelectorAll(options.chipSelector));
    var empty = document.querySelector(options.emptySelector);
    if (!rows.length) return;

    var filter = "all";

    function apply() {
      var visible = 0;
      rows.forEach(function (row) {
        var status = row.getAttribute("data-status") || "";
        var show = filter === "all" || status === filter;
        row.classList.toggle("row-hidden", !show);
        if (show) visible += 1;
      });
      if (empty) empty.hidden = visible > 0;
    }

    chips.forEach(function (chip) {
      chip.addEventListener("click", function () {
        filter = chip.getAttribute(options.filterAttr) || "all";
        chips.forEach(function (item) {
          item.classList.toggle("is-on", item === chip);
        });
        apply();
      });
    });

    apply();
  }

  function chartTheme() {
    if (!window.Chart) return;
    Chart.defaults.font.family = "Poppins, sans-serif";
    Chart.defaults.color = "#8d869c";
    Chart.defaults.plugins.legend.display = false;
    Chart.defaults.plugins.tooltip.backgroundColor = "#1c1232";
    Chart.defaults.plugins.tooltip.padding = 10;
    Chart.defaults.plugins.tooltip.cornerRadius = 10;
  }

  function initStatusCharts() {
    if (!window.Chart) return;
    document.querySelectorAll("[data-status-chart]").forEach(function (canvas) {
      var workforce = canvas.hasAttribute("data-present");
      var labels, data, colors;
      if (workforce) {
        labels = ["Present", "On Leave", "Absent"];
        data = [
          Number(canvas.getAttribute("data-present") || 0),
          Number(canvas.getAttribute("data-leave") || 0),
          Number(canvas.getAttribute("data-absent") || 0)
        ];
        colors = ["#7b2c86", "#d7b4ef", "#f6d5ea"];
        if (!data[0] && !data[1] && !data[2]) {
          labels = ["No attendance yet"];
          data = [1];
          colors = ["#f3e8f5"];
        }
      } else {
        var active = Number(canvas.getAttribute("data-active") || 0);
        var inactive = Number(canvas.getAttribute("data-inactive") || 0);
        if (!active && !inactive) active = 1;
        labels = ["Active", "Inactive"];
        data = [active, inactive];
        colors = ["#a02880", "#f0c6e4"];
      }
      new Chart(canvas, {
        type: "doughnut",
        data: {
          labels: labels,
          datasets: [{
            data: data,
            backgroundColor: colors,
            borderWidth: 0,
            hoverOffset: 4,
            borderRadius: workforce ? 8 : 0,
            spacing: workforce ? 3 : 0
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          cutout: "72%"
        }
      });
    });
  }

  function initAreaCharts() {
    if (!window.Chart) return;
    document.querySelectorAll("[data-area-chart]").forEach(function (canvas) {
      var source = document.getElementById(canvas.getAttribute("data-source"));
      if (!source) return;
      var payload;
      try { payload = JSON.parse(source.textContent || "{}"); }
      catch (err) { return; }
      var labels = payload.labels || [];
      var values = payload.values || [];
      if (!labels.length) return;
      var pinned = !!payload.pin;
      var highlight = Number(payload.highlight);
      if (!Number.isFinite(highlight)) highlight = labels.length - 1;
      var dates = payload.dates || [];
      var noun = payload.noun || "Present";
      new Chart(canvas, {
        type: "line",
        data: {
          labels: labels,
          datasets: [{
            data: values,
            borderColor: "#b0268a",
            backgroundColor: function (context) {
              var chart = context.chart;
              var area = chart.chartArea;
              if (!area) return "rgba(176, 38, 138, 0.16)";
              var gradient = chart.ctx.createLinearGradient(0, area.top, 0, area.bottom);
              gradient.addColorStop(0, "rgba(176, 38, 138, 0.34)");
              gradient.addColorStop(1, "rgba(176, 38, 138, 0.02)");
              return gradient;
            },
            fill: true,
            tension: 0.42,
            borderWidth: 2.6,
            pointRadius: function (ctx) {
              if (!pinned) return 3;
              return ctx.dataIndex === highlight ? 6 : 0;
            },
            pointHoverRadius: 6,
            pointBackgroundColor: "#fff",
            pointBorderColor: "#b0268a",
            pointBorderWidth: 3
          }]
        },
        plugins: pinned ? [{
          id: "attendanceTip",
          afterDraw: function (chart) {
            var meta = chart.getDatasetMeta(0);
            var point = meta.data[highlight];
            if (!point) return;
            var value = chart.data.datasets[0].data[highlight];
            var dateLabel = payload.delta_label || dates[highlight] || "";
            var ctx = chart.ctx;
            var line1 = String(value) + " " + noun;
            ctx.save();
            ctx.font = "600 12px Poppins, sans-serif";
            var titleWidth = ctx.measureText(line1).width;
            ctx.font = "500 11px Poppins, sans-serif";
            var width = Math.max(titleWidth, ctx.measureText(dateLabel).width) + 28;
            var height = dateLabel ? 46 : 32;
            var x = point.x - width / 2;
            var y = point.y - height - 16;
            var area = chart.chartArea;
            if (x < area.left) x = area.left;
            if (x + width > area.right) x = area.right - width;
            if (y < area.top) y = point.y + 16;
            ctx.beginPath();
            var radius = 12;
            ctx.moveTo(x + radius, y);
            ctx.arcTo(x + width, y, x + width, y + height, radius);
            ctx.arcTo(x + width, y + height, x, y + height, radius);
            ctx.arcTo(x, y + height, x, y, radius);
            ctx.arcTo(x, y, x + width, y, radius);
            ctx.closePath();
            ctx.fillStyle = "#7a206e";
            ctx.fill();
            ctx.beginPath();
            ctx.moveTo(point.x - 6, y + height);
            ctx.lineTo(point.x + 6, y + height);
            ctx.lineTo(point.x, y + height + 7);
            ctx.closePath();
            ctx.fill();
            ctx.fillStyle = "#fff";
            ctx.font = "600 12px Poppins, sans-serif";
            ctx.textAlign = "center";
            ctx.fillText(line1, x + width / 2, y + (dateLabel ? 18 : 21));
            if (dateLabel) {
              ctx.font = "600 11px Poppins, sans-serif";
              var positive = dateLabel.charAt(0) === "+";
              var negative = dateLabel.charAt(0) === "-";
              ctx.fillStyle = positive ? "#86efac" : negative ? "#fda4af" : "rgba(255,255,255,0.82)";
              ctx.fillText(dateLabel, x + width / 2, y + 34);
            }
            ctx.restore();
          }
        }] : [],
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: pinned ? {
            tooltip: {
              displayColors: false,
              callbacks: {
                title: function () { return ""; },
                label: function (item) { return item.parsed.y + " " + noun; },
                afterLabel: function (item) { return dates[item.dataIndex] || ""; }
              }
            }
          } : {},
          scales: {
            x: { grid: { display: false }, border: { display: false } },
            y: {
              beginAtZero: !pinned,
              suggestedMin: pinned ? Number(payload.axis_min || 0) : 0,
              suggestedMax: pinned
                ? Number(payload.axis_max || 0)
                : Math.max.apply(null, values.concat([1])) + 1,
              ticks: { precision: 0 },
              grid: { color: "rgba(28, 18, 50, 0.06)" },
              border: { display: false }
            }
          }
        }
      });
    });
  }

  function initBranchMap() {
    var host = document.querySelector("[data-branch-map]");
    if (!host || typeof window.L === "undefined") return;

    var payloadNode = document.getElementById("branchLocationData");
    var locations = [];
    if (payloadNode) {
      try {
        locations = JSON.parse(payloadNode.textContent || "[]");
      } catch (error) {
        locations = [];
      }
    }
    if (!Array.isArray(locations)) locations = [];

    var mapped = locations.filter(function (item) {
      return item && item.has_coordinates && Number.isFinite(Number(item.latitude)) && Number.isFinite(Number(item.longitude));
    });

    var map = window.L.map(host, {
      scrollWheelZoom: false,
      zoomControl: true,
      attributionControl: true
    });

    window.L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 18,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
    }).addTo(map);

    function makeIcon(index) {
      return window.L.divIcon({
        className: "branch-pin-icon",
        html: '<div class="branch-pin-bubble"><span>' + String(index) + "</span></div>",
        iconSize: [28, 28],
        iconAnchor: [14, 26],
        popupAnchor: [0, -24]
      });
    }

    var bounds = [];
    var markersByKey = {};

    mapped.forEach(function (item, index) {
      var lat = Number(item.latitude);
      var lng = Number(item.longitude);
      var marker = window.L.marker([lat, lng], { icon: makeIcon(index + 1) }).addTo(map);
      var popupBits = [
        "<strong>" + String(item.name || "Branch") + "</strong>",
        item.location_label ? "<div>" + String(item.location_label) + "</div>" : "",
        item.address ? "<div>" + String(item.address) + "</div>" : ""
      ].filter(Boolean);
      marker.bindPopup(popupBits.join(""));
      bounds.push([lat, lng]);
      markersByKey[String(lat) + "|" + String(lng) + "|" + String(item.name || "")] = marker;
    });

    if (bounds.length === 1) {
      map.setView(bounds[0], 13);
    } else if (bounds.length > 1) {
      map.fitBounds(bounds, { padding: [36, 36], maxZoom: 13 });
    } else {
      map.setView([20.5937, 78.9629], 4);
    }

    setTimeout(function () {
      map.invalidateSize();
    }, 80);

    document.querySelectorAll("[data-focus-branch]").forEach(function (button) {
      button.addEventListener("click", function () {
        var lat = Number(button.getAttribute("data-lat"));
        var lng = Number(button.getAttribute("data-lng"));
        var name = button.getAttribute("data-name") || "";
        if (!Number.isFinite(lat) || !Number.isFinite(lng)) return;
        map.flyTo([lat, lng], 14, { duration: 0.75 });
        var key = String(lat) + "|" + String(lng) + "|" + String(name);
        var marker = markersByKey[key];
        if (marker) marker.openPopup();
      });
    });
  }

  function boot() {
    initSidebar();
    initUserMenu();
    initGreeting();
    animateCounters();
    chartTheme();
    initStatusCharts();
    initAreaCharts();
    initBranchMap();
    // Status chips on company/employee lists are server-rendered links.
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();
})();
