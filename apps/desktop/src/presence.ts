// Contact is not process liveness. Registration and helper polling are not contact.
export const STALE_AFTER_MS = 5 * 60 * 1000;
export type Presence = {
  app?: string;
  state?: string;
  state_reported_at?: number;
  last_contact_at?: number;
};
const labels: Record<string, string> = {
  working: 'Working', idle: 'Idle', blocked: 'Blocked', done: 'Done',
};
export function presenceText(binding: Presence | undefined, now = Date.now()) {
  const timestamp = (value?: number) => typeof value === 'number' && Number.isFinite(value) && value > 0 && value * 1000 <= now;
  const age = (value: number) => {
    const seconds = Math.floor((now - value * 1000) / 1000);
    return seconds < 60 ? 'just now' : Math.floor(seconds / 60) + ' min ago';
  };
  const report = binding?.state && labels[binding.state];
  const work = report ? 'Last reported: ' + report + ' · ' + (timestamp(binding?.state_reported_at) ? age(binding!.state_reported_at!) : 'report time unknown') : 'Work state not reported';
  const contact = timestamp(binding?.last_contact_at)
    ? (now - binding!.last_contact_at! * 1000 >= STALE_AFTER_MS ? 'No recent contact' : 'Recent contact') + ' · Last contact ' + age(binding!.last_contact_at!)
    : 'Contact unknown';
  const mode = ['mcp', 'pull'].includes(binding?.app || '') ? 'On demand · silence is expected' : binding?.app === 'codex-queue' ? 'Next-turn delivery' : '';
  return {work, contact, mode};
}
