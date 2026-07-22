import { useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { wishlist } from "../lib/wishlist";

/** Botão flutuante com contador da lista de desejos — aparece em toda página, exceto ela mesma. */
export function WishlistFloat() {
  const location = useLocation();
  const [count, setCount] = useState(0);

  useEffect(() => {
    setCount(wishlist.count());
  }, [location]);

  if (location.pathname === "/lista-desejos" || count === 0) {
    return null;
  }

  return (
    <Link
      to="/lista-desejos"
      className="fixed bottom-5 right-5 z-50 inline-flex items-center gap-2 rounded-full bg-accent px-5 py-3 text-sm font-bold text-white shadow-lg transition-transform hover:-translate-y-0.5"
    >
      ♡ Lista de desejos
      <span className="flex h-5 min-w-5 items-center justify-center rounded-full bg-white/25 px-1.5 text-xs">
        {count}
      </span>
    </Link>
  );
}
