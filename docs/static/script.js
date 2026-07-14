const root = document.documentElement;
const year = document.querySelector("#current-year");
const themeColor = document.querySelector("#theme-color");
const themeToggle = document.querySelector(".theme-toggle");
const themeToggleIcon = document.querySelector(".theme-toggle-icon");
const themeLogos = document.querySelectorAll(".theme-logo");

const logoByTheme = {
    light: "static/assets/logo_white.png",
    dark: "static/assets/logo_dark.png",
};

const themeColorByTheme = {
    light: "#f7f7f5",
    dark: "#0f172a",
};

if (year) {
    year.textContent = String(new Date().getFullYear());
}

function preferredTheme() {
    const storedTheme = localStorage.getItem("pixocrop-theme");

    if (storedTheme === "light" || storedTheme === "dark") {
        return storedTheme;
    }

    if (window.matchMedia("(prefers-color-scheme: dark)").matches) {
        return "dark";
    }

    return "light";
}

function applyTheme(theme) {
    const nextTheme = theme === "dark" ? "dark" : "light";
    root.dataset.theme = nextTheme;

    if (themeColor) {
        themeColor.setAttribute("content", themeColorByTheme[nextTheme]);
    }

    themeLogos.forEach((logo) => {
        logo.setAttribute("src", logoByTheme[nextTheme]);
    });

    if (themeToggle) {
        const isDark = nextTheme === "dark";
        themeToggle.setAttribute("aria-pressed", String(isDark));
        themeToggle.setAttribute(
            "aria-label",
            isDark ? "Activer le theme clair" : "Activer le theme sombre",
        );
    }

    if (themeToggleIcon) {
        themeToggleIcon.textContent = nextTheme === "dark" ? "☼" : "☾";
    }
}

applyTheme(preferredTheme());

themeToggle?.addEventListener("click", () => {
    const nextTheme = root.dataset.theme === "dark" ? "light" : "dark";
    localStorage.setItem("pixocrop-theme", nextTheme);
    applyTheme(nextTheme);
});
