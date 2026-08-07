// Drives every ".scanner-trigger" button (see templates/_barcode_scanner.html). Unlike
// combo.js, this uses document-level event delegation and never caches element
// references, because the trigger/dialog can live inside a region an HTMX swap later
// replaces (e.g. the bulk-audit tag-entry form) — delegation and fresh lookups mean it
// keeps working without needing to be re-initialized after a swap.
(function () {
    var activeScanner = null;

    function stopActiveScanner() {
        if (!activeScanner) return;
        var scanner = activeScanner;
        activeScanner = null;
        scanner
            .stop()
            .catch(function () {})
            .finally(function () {
                scanner.clear();
            });
    }

    function startScan(trigger) {
        var dialog = document.getElementById(trigger.dataset.dialog);
        var viewportId = "scanner-viewport-" + trigger.dataset.target;
        var statusEl = dialog.querySelector(".scanner-status");
        statusEl.textContent = "";

        dialog.showModal();

        var scanner = new Html5Qrcode(viewportId);
        activeScanner = scanner;
        scanner
            .start(
                { facingMode: "environment" },
                {
                    fps: 20,
                    qrbox: { width: 280, height: 120 },
                    formatsToSupport: [Html5QrcodeSupportedFormats.CODE_128],
                    videoConstraints: {
                        facingMode: "environment",
                        width: { ideal: 1920 },
                        height: { ideal: 1080 },
                    },
                    experimentalFeatures: { useBarCodeDetectorIfSupported: true },
                },
                function (decodedText) {
                    stopActiveScanner();
                    dialog.close();
                    var input = document.getElementById(trigger.dataset.target);
                    if (input) {
                        input.value = decodedText;
                        input.dispatchEvent(new Event("input", { bubbles: true }));
                        input.dispatchEvent(new Event("change", { bubbles: true }));
                    }
                },
                function () {
                    // Per-frame decode failure while aiming — expected constantly, ignore.
                }
            )
            .catch(function () {
                activeScanner = null;
                statusEl.textContent = "Couldn't access the camera.";
            });
    }

    document.addEventListener("click", function (e) {
        var trigger = e.target.closest(".scanner-trigger");
        if (trigger) {
            startScan(trigger);
            return;
        }

        var cancel = e.target.closest(".scanner-cancel");
        if (cancel) {
            stopActiveScanner();
            cancel.closest("dialog").close();
        }
    });

    // The native "close" event (Esc, backdrop click) doesn't bubble, so listen in the
    // capture phase to catch it regardless of which dialog fires it.
    document.addEventListener(
        "close",
        function (e) {
            if (e.target.matches && e.target.matches(".scanner-dialog")) {
                stopActiveScanner();
            }
        },
        true
    );
})();
