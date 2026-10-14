import { describe, expect, it } from "vitest";
import { isAcceptedImageType } from "./api";

const makeFile = (type: string) => new File(["contenu"], "feuille", { type });

describe("isAcceptedImageType", () => {
  it.each(["image/jpeg", "image/png", "image/webp"])(
    "accepte %s",
    (type) => {
      expect(isAcceptedImageType(makeFile(type))).toBe(true);
    },
  );

  it.each(["image/gif", "image/svg+xml", "application/pdf", "text/plain", ""])(
    "refuse '%s'",
    (type) => {
      expect(isAcceptedImageType(makeFile(type))).toBe(false);
    },
  );
});