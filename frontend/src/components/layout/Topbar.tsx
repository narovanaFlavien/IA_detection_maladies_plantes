import { Bell } from "lucide-react";
import { IconButton } from "../ui/IconButton";
import { SearchInput } from "./SearchInput";
import { UserMenu } from "./UserMenu";

export function Topbar() {
  return (
    <header className="flex items-center justify-between gap-6 border-b border-line bg-white px-8 py-4">
      <SearchInput />

      <div className="flex items-center gap-4">
        <IconButton
          icon={<Bell className="h-[18px] w-[18px]" strokeWidth={2} />}
          label="Notifications"
          hasBadge
        />

        <UserMenu name="Jean Dupont" role="Agronome" />
      </div>
    </header>
  );
}
