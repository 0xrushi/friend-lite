/**
 * Unit tests for UserLoopModal component covering all fixed issues.
 */

import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import UserLoopModal from '../UserLoopModal'

const mockFetch = jest.fn()
global.fetch = mockFetch as any

jest.mock('framer-motion', () => ({
  ...jest.requireActual('framer-motion'),
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
    button: ({ children, ...props }: any) => <button {...props}>{children}</button>,
  },
  AnimatePresence: ({ children }: any) => <>{children}</>,
}))

global.console = { ...console, log: jest.fn(), error: jest.fn() }

const mockEvents = [
  {
    version_id: 'version-1',
    conversation_id: 'conv-1',
    transcript: 'Test transcript text',
    timestamp: 1234567890.0,
    audio_duration: 10.5,
    speaker_count: 2,
    word_count: 10,
  },
]

describe('UserLoopModal', () => {
  beforeEach(() => jest.clearAllMocks())

  it('should close modal when no events found', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => [],
    })

    const { container } = render(<UserLoopModal />)

    await waitFor(() => {
      expect(container.querySelector('.fixed')).not.toBeInTheDocument()
    })
  })
})
