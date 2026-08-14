import type { Variants } from "motion/react";

/** Anak-anaknya muncul berurutan, bukan serempak. */
export const wadah: Variants = {
  sembunyi: {},
  muncul: {
    transition: { staggerChildren: 0.07, delayChildren: 0.05 },
  },
};

/** Naik sedikit sambil memudar masuk. */
export const naik: Variants = {
  sembunyi: { opacity: 0, y: 12 },
  muncul: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.4, ease: [0.22, 1, 0.36, 1] },
  },
};

/** Untuk kartu hasil yang datang belakangan. */
export const kartu: Variants = {
  sembunyi: { opacity: 0, y: 16, scale: 0.98 },
  muncul: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: { duration: 0.35, ease: [0.22, 1, 0.36, 1] },
  },
  keluar: { opacity: 0, y: -8, transition: { duration: 0.2 } },
};
