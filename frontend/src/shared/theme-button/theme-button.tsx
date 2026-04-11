import { Moon, Sun } from "lucide-react";
import { toggleTheme, getTheme } from "../utils/update-html-theme";
import "./theme-button.css"
import { useState } from "react";


export const ThemeButton = () => {
    const [theme, setTheme] = useState(getTheme())
    return (
        <button onClick={() => {setTheme(theme === "light" ? "dark": "light"); toggleTheme()}} className="theme-button">
            {theme === "dark" ? <Moon /> : <Sun />}
        </button>
    );
}