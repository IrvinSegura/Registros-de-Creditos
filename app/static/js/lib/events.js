// App-wide signal so the table and the dashboard refresh after any change
const CREDITS_CHANGED = "credits:changed";

export const onCreditsChanged = handler => document.addEventListener(CREDITS_CHANGED, handler);
export const notifyCreditsChanged = () => document.dispatchEvent(new CustomEvent(CREDITS_CHANGED));
