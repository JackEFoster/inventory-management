import { test } from 'node:test'
import assert from 'node:assert/strict'
import { escapeCsvCell, toCsv } from '../src/utils/csv.js'

test('plain values pass through unquoted', () => {
  assert.equal(escapeCsvCell('SKU-001'), 'SKU-001')
  assert.equal(escapeCsvCell(42), '42')
  assert.equal(escapeCsvCell('12.50'), '12.50')
})

test('null and undefined become empty cells', () => {
  assert.equal(escapeCsvCell(null), '')
  assert.equal(escapeCsvCell(undefined), '')
})

test('commas, quotes and newlines are quoted with quotes doubled', () => {
  assert.equal(escapeCsvCell('Sensor, Type A'), '"Sensor, Type A"')
  assert.equal(escapeCsvCell('5" Display'), '"5"" Display"')
  assert.equal(escapeCsvCell('line1\nline2'), '"line1\nline2"')
})

test('formula-like strings are neutralised but numbers are not', () => {
  assert.equal(escapeCsvCell('=SUM(A1:A9)'), "'=SUM(A1:A9)")
  assert.equal(escapeCsvCell('@cmd'), "'@cmd")
  assert.equal(escapeCsvCell('+1'), "'+1")
  assert.equal(escapeCsvCell(-5), '-5')
})

test('non-ASCII text (Japanese) is preserved', () => {
  assert.equal(escapeCsvCell('在庫あり'), '在庫あり')
})

test('toCsv joins header and rows with CRLF', () => {
  const csv = toCsv(
    ['SKU', 'Name'],
    [
      ['A1', 'Widget'],
      ['B2', 'Gadget, Large']
    ]
  )
  assert.equal(csv, 'SKU,Name\r\nA1,Widget\r\nB2,"Gadget, Large"')
})

test('toCsv with no rows yields just the header', () => {
  assert.equal(toCsv(['SKU'], []), 'SKU')
})
