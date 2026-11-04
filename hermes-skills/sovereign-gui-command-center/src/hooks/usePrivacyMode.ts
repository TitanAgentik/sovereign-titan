import { useCallback, useEffect, useState } from "react";

export function usePrivacyMode(): [boolean, () => void] {
  const [privacyMode, setPrivacyMode] = useState<boolean>(() => {
    try {
      return window.localStorage.getItem("titan_privacy_mode") === "true";
    } catch {
      return false;
    }
  });

  useEffect(() => {
    const syncFromStorage = (ev?: Event) => {
      try {
        if (ev && "detail" in ev) {
          const detail = (ev as CustomEvent<{ enabled?: boolean }>).detail;
          if (typeof detail?.enabled === "boolean") {
            setPrivacyMode(detail.enabled);
            return;
          }
        }
        setPrivacyMode(
          window.localStorage.getItem("titan_privacy_mode") === "true"
        );
      } catch {
        // Ignore storage read errors in restricted webviews
      }
    };

    window.addEventListener("titan-privacy-mode-change", syncFromStorage);
    window.addEventListener("storage", syncFromStorage);
    return () => {
      window.removeEventListener("titan-privacy-mode-change", syncFromStorage);
      window.removeEventListener("storage", syncFromStorage);
    };
  }, []);

  const togglePrivacyMode = useCallback(() => {
    setPrivacyMode((prev) => {
      const next = !prev;
      try {
        window.localStorage.setItem("titan_privacy_mode", String(next));
        window.dispatchEvent(
          new CustomEvent("titan-privacy-mode-change", {
            detail: { enabled: next },
          })
        );
      } catch {
        // Ignore storage write errors in restricted webviews
      }
      return next;
    });
  }, []);

  return [privacyMode, togglePrivacyMode];
}
