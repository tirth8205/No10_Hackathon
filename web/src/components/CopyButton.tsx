import { useEffect, useState } from "react";
import { Button } from "./govuk";

/** Copies text to the clipboard and says so, visibly and to screen readers. */
export function CopyButton({ text, label, variant }: { text: string; label: string; variant?: "secondary" }) {
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!copied) return;
    const timer = setTimeout(() => setCopied(false), 4000);
    return () => clearTimeout(timer);
  }, [copied]);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
    } catch {
      setCopied(false);
    }
  };

  return (
    <>
      <Button variant={variant} onClick={copy}>
        {copied ? "Copied" : label}
      </Button>
      <span className="govuk-visually-hidden" aria-live="polite">
        {copied ? "Copied to clipboard" : ""}
      </span>
    </>
  );
}

/** Saves text as a file in the browser. */
export function downloadText(filename: string, text: string) {
  const url = URL.createObjectURL(new Blob([text], { type: "text/plain;charset=utf-8" }));
  downloadUrl(url, filename);
  URL.revokeObjectURL(url);
}

/** Downloads a file the server builds (or a blob URL) by clicking a hidden link to it. */
export function downloadUrl(url: string, filename?: string) {
  const a = document.createElement("a");
  a.href = url;
  if (filename) a.download = filename;
  a.rel = "noopener";
  a.click();
}
