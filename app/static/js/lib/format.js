const LOCALE = "es-MX";
// Credits do not store a currency; change it here if the portfolio uses another one
const CURRENCY = "MXN";

const currency = new Intl.NumberFormat(LOCALE, { style: "currency", currency: CURRENCY });
const compactCurrency = new Intl.NumberFormat(LOCALE, {
    style: "currency", currency: CURRENCY, notation: "compact", maximumFractionDigits: 1,
});
const decimal = new Intl.NumberFormat(LOCALE, { maximumFractionDigits: 2 });
const integer = new Intl.NumberFormat(LOCALE);
// ISO dates are read as UTC so they never shift a day in negative offsets
const date = new Intl.DateTimeFormat(LOCALE, { dateStyle: "medium", timeZone: "UTC" });
const month = new Intl.DateTimeFormat(LOCALE, { month: "short", year: "numeric", timeZone: "UTC" });
const shortMonth = new Intl.DateTimeFormat(LOCALE, { month: "short", timeZone: "UTC" });
// Timestamps are shown in the viewer's own time zone
const dateTime = new Intl.DateTimeFormat(LOCALE, { dateStyle: "medium", timeStyle: "short" });

export const formatCurrency = value => currency.format(Number(value));
export const formatCompactCurrency = value => compactCurrency.format(Number(value));
export const formatPercent = value => `${decimal.format(Number(value))} %`;
export const formatInteger = value => integer.format(Number(value));
export const formatMonths = value => `${decimal.format(Number(value))} ${Number(value) === 1 ? "mes" : "meses"}`;
export const formatDate = isoDate => date.format(new Date(`${isoDate}T00:00:00Z`));
export const formatMonth = (year, monthNumber) => month.format(Date.UTC(year, monthNumber - 1, 1));

// ["15", "nov"] for a calendar-style date badge
export function formatDayMonth(isoDate) {
    const value = new Date(`${isoDate}T00:00:00Z`);
    return [String(value.getUTCDate()), shortMonth.format(value).replace(".", "")];
}

// The API stores timestamps in UTC; values without an offset are read as UTC
export function formatDateTime(isoDateTime) {
    const hasOffset = /([zZ]|[+-]\d{2}:?\d{2})$/.test(isoDateTime);
    return dateTime.format(new Date(hasOffset ? isoDateTime : `${isoDateTime}Z`));
}

export function initials(name) {
    return name.split(" ").filter(Boolean).slice(0, 2).map(part => part[0]).join("").toUpperCase();
}

// Local calendar date as YYYY-MM-DD, for date inputs
export function todayIso() {
    const now = new Date();
    return new Date(now.getTime() - now.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
}
