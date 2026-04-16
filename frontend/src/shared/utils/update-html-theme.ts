export function toggleTheme() {
    const currentTheme: string = getTheme()
    const newTheme: string = currentTheme === "light" ? "dark": "light"
    const html = document.querySelector('html');
    html?.style.setProperty('color-scheme', newTheme);
    localStorage.setItem("theme", newTheme)
}

export function getTheme(){
    return localStorage.getItem("theme") || "light"
}

export function setInitialTheme(){
    const theme = getTheme() || "light"
    const html = document.querySelector('html');
    html?.style.setProperty('color-scheme', theme);
}