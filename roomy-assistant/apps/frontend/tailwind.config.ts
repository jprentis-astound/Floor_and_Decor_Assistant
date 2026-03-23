import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        "fd-green": "#1B5E20",
        "fd-green-light": "#E8F5E9",
        "fd-red": "#CC0000",
        "fd-blue": "#1565C0",
      },
    },
  },
  plugins: [],
};

export default config;
