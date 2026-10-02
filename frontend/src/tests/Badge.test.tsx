import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Badge } from '../components/ui/Badge';

describe('Badge Component', () => {
  it('renders correct text for Healthy badge', () => {
    render(<Badge value="Healthy" variant="health" />);
    expect(screen.getByText('Healthy')).toBeDefined();
  });

  it('renders correct text for Critical badge', () => {
    render(<Badge value="Critical" variant="health" />);
    expect(screen.getByText('Critical')).toBeDefined();
  });

  it('renders Demo badge text accurately', () => {
    render(<Badge variant="demo">Demo / Simulated Data</Badge>);
    expect(screen.getByText('Demo / Simulated Data')).toBeDefined();
  });
});
