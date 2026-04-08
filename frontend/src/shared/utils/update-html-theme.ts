export function setHtmlTheme(theme: string = localStorage.getItem("theme") || "light") {
    const html = document.querySelector('html');
    html?.style.setProperty('color-scheme', theme);
}