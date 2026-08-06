// Drives every ".combo" search-as-you-type widget on the page (the actual
// search results come from the server via HTMX; this just wires up
// selection, keyboard navigation, and clearing stale hidden values).
(function () {
    function items(combo) {
        return combo.querySelectorAll(".combo-option[data-id]");
    }

    function highlighted(combo) {
        return combo.querySelector(".combo-option.active");
    }

    function highlight(combo, opt) {
        var current = highlighted(combo);
        if (current) current.classList.remove("active");
        if (opt) {
            opt.classList.add("active");
            opt.scrollIntoView({ block: "nearest" });
        }
    }

    function setSelectedName(combo, text) {
        var label = combo.querySelector(".combo-selected-name");
        if (label) label.textContent = text || "";
    }

    function selectOption(combo, opt) {
        if (!opt || !opt.dataset.id) return;
        combo.querySelector("input[type=hidden]").value = opt.dataset.id;
        combo.querySelector(".combo-search").value = opt.dataset.value;
        setSelectedName(combo, opt.dataset.label);
        combo.querySelector(".combo-options").innerHTML = "";
    }

    document.querySelectorAll(".combo").forEach(function (combo) {
        var search = combo.querySelector(".combo-search");
        var options = combo.querySelector(".combo-options");
        var hidden = combo.querySelector("input[type=hidden]");

        search.addEventListener("input", function () {
            // Require an explicit pick from the dropdown rather than
            // silently keeping whatever value was previously selected.
            hidden.value = "";
            setSelectedName(combo, "");
        });

        search.addEventListener("keydown", function (e) {
            var list = items(combo);
            if (!list.length) return;
            var current = highlighted(combo);
            var index = current ? Array.prototype.indexOf.call(list, current) : -1;

            if (e.key === "ArrowDown") {
                e.preventDefault();
                highlight(combo, list[Math.min(index + 1, list.length - 1)]);
            } else if (e.key === "ArrowUp") {
                e.preventDefault();
                highlight(combo, list[Math.max(index - 1, 0)]);
            } else if (e.key === "Enter") {
                e.preventDefault();
                selectOption(combo, current || list[0]);
            }
        });

        options.addEventListener("click", function (e) {
            selectOption(combo, e.target.closest(".combo-option"));
        });
    });

    document.addEventListener("click", function (e) {
        var current = e.target.closest(".combo");
        document.querySelectorAll(".combo").forEach(function (combo) {
            if (combo !== current) {
                combo.querySelector(".combo-options").innerHTML = "";
            }
        });
    });
})();
