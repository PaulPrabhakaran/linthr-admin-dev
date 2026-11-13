(function () {
  function getCookie(name) {
    var match = document.cookie.match(new RegExp('(?:^|; )' + name.replace(/([.$?*|{}()[\]\\/+^])/g, '\\$1') + '=([^;]*)'));
    return match ? decodeURIComponent(match[1]) : '';
  }

  function csrfToken() {
    var input = document.querySelector('[name=csrfmiddlewaretoken]');
    return (input && input.value) || getCookie('csrftoken') || '';
  }

  function escapeHtml(value) {
    return String(value || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function iconSvg(kind) {
    if (kind === 'activate' || kind === 'success') {
      return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M20 6 9 17l-5-5"/></svg>';
    }
    if (kind === 'error') {
      return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M18 6 6 18M6 6l12 12"/></svg>';
    }
    return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 8v5"/><path d="M12 16.5h.01"/><path d="M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18Z"/></svg>';
  }

  function companyCardHtml(opts) {
    var tone = opts.tone || 'deactivate';
    return (
      '<div class="swal-company-card">' +
        '<div class="swal-company-icon is-' + tone + '">' + iconSvg(tone) + '</div>' +
        '<div class="swal-company-kicker">' + escapeHtml(opts.kicker || 'Company status') + '</div>' +
        '<h3 class="swal-company-title">' + escapeHtml(opts.title) + '</h3>' +
        '<p class="swal-company-copy">' + (opts.copyHtml || '') + '</p>' +
      '</div>'
    );
  }

  function fireCompanySwal(opts) {
    if (!window.Swal) return Promise.resolve({ isConfirmed: false });
    return Swal.fire({
      html: companyCardHtml(opts),
      showCancelButton: !!opts.showCancelButton,
      confirmButtonText: opts.confirmButtonText || 'OK',
      cancelButtonText: opts.cancelButtonText || 'Cancel',
      reverseButtons: true,
      focusCancel: !!opts.showCancelButton,
      timer: opts.timer || undefined,
      showConfirmButton: opts.timer ? false : opts.showConfirmButton !== false,
      buttonsStyling: true,
      customClass: {
        popup: 'swal-company swal-company-' + (opts.tone || 'neutral'),
        confirmButton: opts.confirmClass || 'swal-confirm-ok',
        cancelButton: 'swal-cancel',
        backdrop: 'swal-company-backdrop',
      },
      showClass: { popup: 'swal2-show' },
      hideClass: { popup: 'swal2-hide' },
    });
  }

  var POWER_ICON =
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3v8"/><path d="M8.5 6.2a7 7 0 1 0 7 0"/></svg>';
  var CHECK_ICON =
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5"/></svg>';

  function syncButton(btn, active) {
    var isActive = !!active;
    btn.dataset.active = isActive ? 'true' : 'false';
    btn.classList.toggle('btn-danger', isActive);
    btn.classList.toggle('btn-success', !isActive);
    btn.classList.toggle('is-deactivate', isActive);
    btn.classList.toggle('is-activate', !isActive);

    var label = btn.querySelector('[data-active-label]');
    if (label) {
      label.textContent = isActive ? 'Deactivate' : 'Activate';
    } else {
      btn.textContent = isActive ? 'Deactivate' : 'Activate';
    }

    var icon = btn.querySelector('[data-active-icon]');
    if (icon) {
      icon.classList.toggle('is-deactivate', isActive);
      icon.classList.toggle('is-activate', !isActive);
      icon.innerHTML = isActive ? POWER_ICON : CHECK_ICON;
    }
  }

  function closeAllRowMenus(exceptMenu) {
    document.querySelectorAll('.row-menu.is-open').forEach(function (menu) {
      if (exceptMenu && menu === exceptMenu) return;
      menu.classList.remove('is-open', 'is-up');
      var trigger = menu.querySelector('.row-menu-trigger');
      var panel = menu.querySelector('.row-menu-panel');
      if (trigger) trigger.setAttribute('aria-expanded', 'false');
      if (panel) panel.hidden = true;
    });
    document.querySelectorAll('.data-table-wrap.has-open-menu').forEach(function (wrap) {
      if (exceptMenu && wrap.contains(exceptMenu)) return;
      wrap.classList.remove('has-open-menu');
    });
  }

  function openRowMenu(menu) {
    var trigger = menu.querySelector('.row-menu-trigger');
    var panel = menu.querySelector('.row-menu-panel');
    if (!trigger || !panel) return;

    closeAllRowMenus(menu);
    menu.classList.add('is-open');
    trigger.setAttribute('aria-expanded', 'true');
    panel.hidden = false;

    var wrap = menu.closest('.data-table-wrap');
    if (wrap) wrap.classList.add('has-open-menu');

    var rect = panel.getBoundingClientRect();
    if (rect.bottom > window.innerHeight - 12) {
      menu.classList.add('is-up');
    } else {
      menu.classList.remove('is-up');
    }
  }

  function toggleRowMenu(menu) {
    if (menu.classList.contains('is-open')) {
      closeAllRowMenus();
    } else {
      openRowMenu(menu);
    }
  }

  function syncStatusBadges(companyId, active) {
    document.querySelectorAll('[data-company-status][data-company-id="' + companyId + '"]').forEach(function (el) {
      var kind = el.getAttribute('data-company-status');
      if (kind === 'badge') {
        el.classList.toggle('badge-ok', active);
        el.classList.toggle('badge-off', !active);
        el.textContent = active ? 'Active' : 'Inactive';
      } else if (kind === 'pill') {
        el.classList.toggle('is-live', active);
        el.innerHTML = active ? '<i></i>Active' : 'Inactive';
      }
    });
  }

  async function setCompanyActive(btn, nextActive) {
    var url = btn.getAttribute('data-url');
    if (!url) return;

    btn.disabled = true;
    try {
      var response = await fetch(url, {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken(),
          Accept: 'application/json',
        },
        body: JSON.stringify({ active: nextActive }),
      });
      var payload = {};
      try {
        payload = await response.json();
      } catch (_err) {
        payload = {};
      }
      if (!response.ok || !payload.success) {
        throw new Error(payload.message || 'Unable to update company status.');
      }

      var active = !!(payload.data && typeof payload.data.active === 'boolean'
        ? payload.data.active
        : nextActive);

      var companyId = btn.dataset.companyId;
      document.querySelectorAll('.js-company-active[data-company-id="' + companyId + '"]').forEach(function (node) {
        syncButton(node, active);
      });
      syncStatusBadges(companyId, active);

      fireCompanySwal({
        tone: 'success',
        kicker: active ? 'Now live' : 'Now paused',
        title: active ? 'Company activated' : 'Company deactivated',
        copyHtml: escapeHtml(
          payload.message ||
            (active
              ? 'Access is restored and the company is available again.'
              : 'Tenant access is paused until you activate it again.')
        ),
        name: btn.getAttribute('data-company-name') || '',
        timer: 1900,
        showConfirmButton: false,
      });
    } catch (err) {
      fireCompanySwal({
        tone: 'error',
        kicker: 'Something went wrong',
        title: 'Update failed',
        copyHtml: escapeHtml((err && err.message) || 'Unable to update company status.'),
        confirmButtonText: 'Close',
        confirmClass: 'swal-confirm-ok',
      });
    } finally {
      btn.disabled = false;
    }
  }

  function confirmAndToggle(btn) {
    var name = btn.getAttribute('data-company-name') || 'this company';
    var currentlyActive = btn.dataset.active === 'true';
    var nextActive = !currentlyActive;
    var actionLabel = nextActive ? 'Activate' : 'Deactivate';
    var tone = nextActive ? 'activate' : 'deactivate';

    if (!window.Swal) {
      if (window.confirm(actionLabel + ' ' + name + '?')) {
        setCompanyActive(btn, nextActive);
      }
      return;
    }

    fireCompanySwal({
      tone: tone,
      kicker: nextActive ? 'Bring online' : 'Pause access',
      title: nextActive ? 'Activate this company?' : 'Deactivate this company?',
      copyHtml: nextActive
        ? 'This will restore platform access for <strong>' + escapeHtml(name) + '</strong>.'
        : 'This will pause platform access for <strong>' + escapeHtml(name) + '</strong> until activated again.',
      name: name,
      showCancelButton: true,
      confirmButtonText: 'Yes, ' + actionLabel.toLowerCase(),
      cancelButtonText: 'Keep as is',
      confirmClass: nextActive ? 'swal-confirm-activate' : 'swal-confirm-deactivate',
    }).then(function (result) {
      if (result.isConfirmed) {
        setCompanyActive(btn, nextActive);
      }
    });
  }

  document.addEventListener('click', function (event) {
    var trigger = event.target.closest('.row-menu-trigger');
    if (trigger) {
      event.preventDefault();
      event.stopPropagation();
      var menu = trigger.closest('.row-menu');
      if (menu) toggleRowMenu(menu);
      return;
    }

    var btn = event.target.closest('.js-company-active');
    if (btn) {
      event.preventDefault();
      closeAllRowMenus();
      confirmAndToggle(btn);
      return;
    }

    if (!event.target.closest('.row-menu')) {
      closeAllRowMenus();
    }
  });

  document.addEventListener('keydown', function (event) {
    if (event.key === 'Escape') closeAllRowMenus();
  });
})();
