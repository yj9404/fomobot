import { useEffect, useState } from 'react'
import { FONT } from '../tokens'

const TOAST_MS = 3000

/** 화면 아래에 잠깐 떴다 사라지는 안내. [그릴 요소, 띄우는 함수]를 준다. */
export function useToast(): [React.ReactNode, (message: string) => void] {
  const [message, setMessage] = useState<string | null>(null)

  useEffect(() => {
    if (message == null) return
    const id = setTimeout(() => setMessage(null), TOAST_MS)
    return () => clearTimeout(id)
  }, [message])

  const node = message != null && (
    <div role="status" style={{
      position: 'fixed', left: 16, right: 16, bottom: 'calc(16px + env(safe-area-inset-bottom))', zIndex: 20,
      padding: '12px 16px', borderRadius: 12, background: 'rgba(17,24,39,0.92)', color: '#fff',
      fontSize: 13.5, fontFamily: FONT.sans, textAlign: 'center',
    }}>
      {message}
    </div>
  )

  return [node, setMessage]
}
