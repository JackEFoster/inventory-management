// Spreadsheet apps execute cells that start with these characters as formulas
// ("CSV injection"). Only string cells are guarded so negative numbers survive.
const FORMULA_TRIGGERS = /^[=+\-@\t\r]/

/**
 * Escape one value for CSV (RFC 4180): quote it when it contains a comma,
 * quote, or newline, doubling any embedded quotes.
 */
export function escapeCsvCell(value) {
  if (value === null || value === undefined) return ''
  let text = String(value)
  if (typeof value === 'string' && FORMULA_TRIGGERS.test(text)) {
    text = `'${text}`
  }
  if (/[",\r\n]/.test(text)) {
    return `"${text.replace(/"/g, '""')}"`
  }
  return text
}

/**
 * Build CSV text from a header row and data rows (arrays of values).
 * Uses CRLF line endings, which RFC 4180 specifies and Excel expects.
 */
export function toCsv(headers, rows) {
  return [headers, ...rows].map((row) => row.map(escapeCsvCell).join(',')).join('\r\n')
}

/**
 * Trigger a browser download of CSV text. A UTF-8 BOM is prepended so Excel
 * detects the encoding; without it Japanese product names show as mojibake.
 */
export function downloadCsv(filename, csvText) {
  const blob = new Blob(['﻿' + csvText], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}
