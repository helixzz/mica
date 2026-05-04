import { notification } from 'antd'

export function showUndoToast(
  msg: string,
  onUndo: () => void,
  duration = 5
) {
  const key = `undo-${Date.now()}`
  notification.info({
    key,
    message: msg,
    duration,
    btn: (
      <button
        onClick={() => { notification.destroy(key); onUndo() }}
        style={{ cursor: 'pointer', background: 'none', border: 'none', color: '#1890ff', fontWeight: 500, padding: 0 }}
      >
        Undo
      </button>
    ),
  })
}
