"use client";

import { useEffect, useRef, useState } from "react";
import { formatCurrency } from "@/lib/format";

interface PriceFlashProps {
  price: number;
  direction: "up" | "down" | "flat" | string;
  className?: string;
}

export function PriceFlash({
  price,
  direction,
  className = "",
}: PriceFlashProps) {
  const [flash, setFlash] = useState<"up" | "down" | null>(null);
  const prevPrice = useRef(price);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (price !== prevPrice.current) {
      if (timerRef.current) clearTimeout(timerRef.current);

      setFlash(
        direction === "up" ? "up" : direction === "down" ? "down" : null
      );
      prevPrice.current = price;

      timerRef.current = setTimeout(() => {
        setFlash(null);
        timerRef.current = null;
      }, 500);
    }

    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [price, direction]);

  return (
    <span
      className={`inline-block rounded px-1 transition-colors duration-500 ease-out ${
        flash === "up" ? "bg-price-up/30" : ""
      } ${flash === "down" ? "bg-price-down/30" : ""} ${className}`}
    >
      {formatCurrency(price)}
    </span>
  );
}
