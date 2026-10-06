// File pickers. The screens hand chosen files to an `onFiles` callback; sending
// them anywhere is the back end's job.

import { useId, useState, type DragEvent, type ReactNode } from "react";
import { cx } from "./govuk";

const ACCEPT = "image/*,application/pdf,.doc,.docx,.txt,.eml";

function FileButton({
  label,
  onFiles,
  capture,
  variant,
  icon,
  multiple = true,
}: {
  label: string;
  onFiles: (files: File[]) => void;
  capture?: boolean;
  variant?: "secondary";
  icon?: ReactNode;
  multiple?: boolean;
}) {
  const id = useId();
  return (
    <div className="app-file-button">
      <input
        id={id}
        className="app-file-button__input"
        type="file"
        accept={capture ? "image/*" : ACCEPT}
        capture={capture ? "environment" : undefined}
        multiple={multiple}
        onChange={(event) => {
          const files = Array.from(event.target.files ?? []);
          if (files.length) onFiles(files);
          event.target.value = "";
        }}
      />
      <label htmlFor={id} className={cx("govuk-button app-file-button__label", variant && `govuk-button--${variant}`)}>
        {icon}
        {label}
      </label>
    </div>
  );
}

const CameraIcon = () => (
  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false">
    <path d="M3 8h3.5l2-3h7l2 3H21v12H3z" />
    <circle cx="12" cy="13.5" r="3.5" />
  </svg>
);

/** A file picker that reads as a link, for secondary routes such as "Add it here". */
export function FileLink({ label, onFiles }: { label: string; onFiles: (files: File[]) => void }) {
  const id = useId();
  return (
    <span className="app-file-button app-file-button--link">
      <input
        id={id}
        className="app-file-button__input"
        type="file"
        accept={ACCEPT}
        multiple
        onChange={(event) => {
          const files = Array.from(event.target.files ?? []);
          if (files.length) onFiles(files);
          event.target.value = "";
        }}
      />
      <label htmlFor={id} className="govuk-link app-file-button__label">
        {label}
      </label>
    </span>
  );
}

/** The client's two big buttons: camera, or a file already on the phone. */
export function PhoneUpload({ onFiles }: { onFiles: (files: File[]) => void }) {
  return (
    <div className="app-phone-upload">
      <FileButton label="Take photos" capture onFiles={onFiles} icon={<CameraIcon />} />
      <FileButton label="Choose from your phone" variant="secondary" onFiles={onFiles} />
    </div>
  );
}

/**
 * The client's upload: camera first on a phone or tablet; drag and drop with a file button
 * on a computer, where there is usually no camera to take photos with.
 */
export function ClientFilePicker({ phone, onFiles }: { phone: boolean; onFiles: (files: File[]) => void }) {
  if (phone) return <PhoneUpload onFiles={onFiles} />;
  return (
    <DropZone
      primary
      label="Drag your letter here"
      hint="Or choose a PDF, Word file, scan or photo from your computer."
      buttonLabel="Choose a file"
      onFiles={onFiles}
    />
  );
}

/** Drop zone for the solicitor's desktop, with a button for keyboard and touch users. */
export function DropZone({
  label,
  hint,
  onFiles,
  compact,
  primary,
  buttonLabel = "Choose file",
}: {
  label: string;
  hint?: string;
  onFiles: (files: File[]) => void;
  compact?: boolean;
  /** Make the file button the page's main action. */
  primary?: boolean;
  buttonLabel?: string;
}) {
  const [over, setOver] = useState(false);
  const onDrop = (event: DragEvent) => {
    event.preventDefault();
    setOver(false);
    const files = Array.from(event.dataTransfer.files);
    if (files.length) onFiles(files);
  };
  return (
    <div
      className={cx("app-drop-zone", compact && "app-drop-zone--compact", over && "app-drop-zone--over")}
      onDragOver={(event) => {
        event.preventDefault();
        setOver(true);
      }}
      onDragLeave={() => setOver(false)}
      onDrop={onDrop}
    >
      <div className="app-drop-zone__text">
        <p className="govuk-body govuk-!-font-weight-bold govuk-!-margin-bottom-1">{label}</p>
        {hint && <p className="govuk-body-s app-secondary-text govuk-!-margin-bottom-0">{hint}</p>}
      </div>
      <FileButton label={buttonLabel} variant={primary ? undefined : "secondary"} onFiles={onFiles} />
    </div>
  );
}
