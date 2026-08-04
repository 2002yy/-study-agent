import { useEffect, useRef } from "react";

export function useResetResearchSelectionOnSessionChange(
  activeChatThreadId: string | undefined,
  setUseInChat: (value: boolean) => void,
) {
  const previousThreadId = useRef(activeChatThreadId);

  useEffect(() => {
    if (previousThreadId.current !== activeChatThreadId) {
      setUseInChat(false);
    }
    previousThreadId.current = activeChatThreadId;
  }, [activeChatThreadId, setUseInChat]);
}
