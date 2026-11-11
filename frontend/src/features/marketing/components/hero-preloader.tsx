"use client";

import { useEffect } from "react";
import { getImageProps } from "next/image";
import { HERO_IMAGES, HERO_SIZES } from "../hero-images";

/**
 * Once the page is idle, downloads every page's hero photo into the browser
 * cache, so opening another page shows its photo without waiting. Skipped
 * when the visitor asked to save data.
 */
export function HeroPreloader() {
  useEffect(() => {
    const connection = (navigator as Navigator & { connection?: { saveData?: boolean } })
      .connection;
    if (connection?.saveData) return;

    const preload = () => {
      for (const image of Object.values(HERO_IMAGES)) {
        const { props } = getImageProps({ src: image, alt: "", sizes: HERO_SIZES });
        const img = new window.Image();
        img.decoding = "async";
        img.sizes = HERO_SIZES;
        if (props.srcSet) img.srcset = props.srcSet;
        img.src = props.src;
      }
    };

    // Safari has no requestIdleCallback.
    if (typeof window.requestIdleCallback === "function") {
      const id = window.requestIdleCallback(preload, { timeout: 3000 });
      return () => window.cancelIdleCallback(id);
    }
    const timer = setTimeout(preload, 1500);
    return () => clearTimeout(timer);
  }, []);

  return null;
}
