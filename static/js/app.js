(function () {
  document.querySelectorAll('[data-confirm]').forEach((el) => {
    el.addEventListener('click', (event) => {
      if (!window.confirm(el.dataset.confirm || 'آیا مطمئن هستید؟')) event.preventDefault();
    });
  });
  document.querySelectorAll('input[type=file]').forEach((input) => {
    input.addEventListener('change', () => {
      const target = input.closest('label')?.querySelector('[data-file-name]');
      if (target) target.textContent = input.files?.[0]?.name || 'فایلی انتخاب نشده است';
    });
  });
})();
