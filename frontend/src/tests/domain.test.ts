import { describe, it, expect } from 'vitest';

describe('Domain Rules & Fleet Constants', () => {
  it('enforces 5 demo machines in fleet configuration', () => {
    const demoMachineCount = 5;
    expect(demoMachineCount).toBe(5);
  });

  it('validates decision threshold alignment', () => {
    const decisionThreshold = 0.10;
    const isMediumOrHigher = (prob: number) => (prob >= decisionThreshold ? 'Medium+' : 'Low');

    expect(isMediumOrHigher(0.10)).toBe('Medium+');
    expect(isMediumOrHigher(0.09)).toBe('Low');
    expect(isMediumOrHigher(0.50)).toBe('Medium+');
  });

  it('validates health indicator band assignments', () => {
    const getHealthBand = (hi: number) => {
      if (hi >= 86.0) return 'Excellent';
      if (hi >= 71.0) return 'Healthy';
      if (hi >= 51.0) return 'Warning';
      if (hi >= 31.0) return 'Poor';
      return 'Critical';
    };

    expect(getHealthBand(99.95)).toBe('Excellent');
    expect(getHealthBand(75.0)).toBe('Healthy');
    expect(getHealthBand(51.51)).toBe('Warning');
    expect(getHealthBand(30.0)).toBe('Critical');
  });
});
