import { toggleTheme, getTheme, setInitialTheme } from "./utils/update-html-theme";
import { ThemeButton } from "./theme-button/theme-button";
import { ProfileParams } from "./api/utils/types";
import { profileApi } from "./api/users";

export {toggleTheme, getTheme, setInitialTheme, ThemeButton, profileApi};
export type {ProfileParams}