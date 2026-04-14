import { toggleTheme, getTheme, setInitialTheme } from "./utils/update-html-theme";
import { ThemeButton } from "./theme-button/theme-button";
import { Course, ProfileParams } from "./api/utils/types";
import { profileApi } from "./api/users";
import { BaselineResponse } from "./api/utils/types";

export {toggleTheme, getTheme, setInitialTheme, ThemeButton, profileApi};
export type {ProfileParams, BaselineResponse, Course}