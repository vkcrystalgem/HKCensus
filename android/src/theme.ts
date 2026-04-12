import { Platform } from "react-native";

export const palette = {
  bg: "#F2ECDF",
  paper: "#FFF8EE",
  panel: "#FFFDF7",
  ink: "#1D1D1B",
  muted: "#625F57",
  border: "rgba(98,95,87,0.16)",
  borderSoft: "rgba(98,95,87,0.12)",
  teal: "#0F766E",
  orange: "#C2410C",
  gold: "#A16207",
  blue: "#1D4ED8",
  red: "#B91C1C",
  slate: "#334155",
  green: "#15803D",
  indigo: "#4338CA",
  rose: "#BE123C",
  brown: "#7C2D12",
};

export const shadows = {
  card: Platform.select({
    android: {
      elevation: 3,
    },
    default: {
      shadowColor: "#000",
      shadowOpacity: 0.08,
      shadowRadius: 18,
      shadowOffset: { width: 0, height: 8 },
    },
  }),
};
