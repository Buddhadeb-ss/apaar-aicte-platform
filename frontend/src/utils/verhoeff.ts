// Verhoeff algorithm multiplication and permutation matrices
const verhoeffD: number[][] = [
  [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
  [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
  [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
  [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
  [4, 0, 1, 2, 3, 9, 5, 6, 7, 8],
  [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
  [6, 5, 9, 8, 7, 1, 0, 4, 3, 2],
  [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
  [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
  [9, 8, 7, 6, 5, 4, 3, 2, 1, 0]
];

const verhoeffP: number[][] = [
  [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
  [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
  [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
  [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
  [9, 4, 5, 3, 1, 2, 6, 8, 7, 0],
  [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
  [2, 7, 9, 3, 8, 0, 6, 4, 1, 5],
  [7, 0, 4, 6, 9, 1, 3, 2, 5, 8]
];

export function cleanApaar(raw: string): string {
  if (!raw) return '';
  return raw.replace(/[^0-9]/g, '').trim();
}

export function validateVerhoeffChecksum(numStr: string): boolean {
  let c = 0;
  const reversed = numStr.split('').reverse().map(Number);
  for (let i = 0; i < reversed.length; i++) {
    c = verhoeffD[c][verhoeffP[i % 8][reversed[i]]];
  }
  return c === 0;
}

export function validateApaarId(raw: string): { isValid: boolean; error?: string } {
  const cleaned = cleanApaar(raw);
  if (!cleaned) {
    return { isValid: false, error: 'APAAR ID is required.' };
  }
  if (cleaned.length !== 12) {
    return { isValid: false, error: `APAAR ID must be exactly 12 numeric digits (currently ${cleaned.length}).` };
  }
  if (!validateVerhoeffChecksum(cleaned)) {
    return { isValid: false, error: 'Invalid Verhoeff checksum digit. Please verify the 12th digit.' };
  }
  return { isValid: true };
}

export function maskApaarId(raw: string): string {
  const cleaned = cleanApaar(raw);
  if (cleaned.length < 4) return '•••• •••• ••••';
  const lastFour = cleaned.slice(-4);
  return `•••• •••• ${lastFour}`;
}
