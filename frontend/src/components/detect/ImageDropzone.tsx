import { useCallback, useRef, useState } from "react";
import { UploadCloud } from "lucide-react";
import { ACCEPTED_IMAGE_TYPES } from "../../types/prediction";
import { Button } from "../ui/Button";

interface ImageDropzoneProps {
  onFileSelected: (file: File) => void;
}

export function ImageDropzone({ onFileSelected }: ImageDropzoneProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [isDragActive, setIsDragActive] = useState(false);

  const handleFiles = useCallback(
    (fileList: FileList | null) => {
      const file = fileList?.[0];
      if (file) onFileSelected(file);
    },
    [onFileSelected],
  );

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={() => inputRef.current?.click()}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          inputRef.current?.click();
        }
      }}
      onDragOver={(event) => {
        event.preventDefault();
        setIsDragActive(true);
      }}
      onDragLeave={() => setIsDragActive(false)}
      onDrop={(event) => {
        event.preventDefault();
        setIsDragActive(false);
        handleFiles(event.dataTransfer.files);
      }}
      className={[
        "flex cursor-pointer flex-col items-center justify-center gap-4 rounded-2xl border-2 border-dashed px-6 py-16 text-center transition-colors",
        isDragActive
          ? "border-moss-500 bg-parchment-100"
          : "border-line bg-white hover:border-moss-500/60 hover:bg-parchment-100/60",
      ].join(" ")}
    >
      <span className="flex h-12 w-12 items-center justify-center rounded-full bg-parchment-100 text-moss-600">
        <UploadCloud className="h-6 w-6" strokeWidth={2} />
      </span>

      <div>
        <p className="font-medium text-ink-900">
          Glissez-déposez une photo de feuille ici
        </p>
        <p className="mt-1 text-sm text-ink-400">
          JPEG, PNG ou WEBP — 10 Mo maximum
        </p>
      </div>

      <Button
        type="button"
        variant="dark"
        size="sm"
        onClick={(event) => {
          event.stopPropagation();
          inputRef.current?.click();
        }}
      >
        Téléverser une image
      </Button>

      <input
        ref={inputRef}
        type="file"
        accept={ACCEPTED_IMAGE_TYPES.join(",")}
        className="hidden"
        onChange={(event) => {
          handleFiles(event.target.files);
          event.target.value = "";
        }}
      />
    </div>
  );
}
