// Drives the shared "#lightbox" dialog (see templates/base.html) for full-size image
// previews. Like scanner.js, this uses document-level event delegation because the
// trigger links (".image-thumb") can live inside a region an HTMX swap later replaces
// (e.g. the bulk-audit item list).
(function () {
    document.addEventListener("click", function (e) {
        var trigger = e.target.closest("a.image-thumb");
        if (trigger) {
            e.preventDefault();
            var dialog = document.getElementById("lightbox");
            var img = dialog.querySelector(".lightbox-image");
            var innerImg = trigger.querySelector("img");
            img.src = trigger.href;
            img.alt = innerImg ? innerImg.alt : "";
            dialog.showModal();
            return;
        }

        var closeBtn = e.target.closest(".lightbox-close");
        if (closeBtn) {
            closeBtn.closest("dialog").close();
            return;
        }

        // Clicking the backdrop targets the dialog element itself (nothing inside it).
        var dialog2 = e.target.closest("dialog.lightbox");
        if (dialog2 && e.target === dialog2) {
            dialog2.close();
        }
    });

    // The native "close" event doesn't bubble, so listen in the capture phase. Clear
    // the image src so a large decoded photo isn't held onto after closing.
    document.addEventListener(
        "close",
        function (e) {
            if (e.target.matches && e.target.matches("dialog.lightbox")) {
                var img = e.target.querySelector(".lightbox-image");
                if (img) img.src = "";
            }
        },
        true
    );
})();
