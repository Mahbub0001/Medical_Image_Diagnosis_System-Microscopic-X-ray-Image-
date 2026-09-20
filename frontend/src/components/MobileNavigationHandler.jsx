import React, { useEffect } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { Capacitor } from "@capacitor/core";
import { App as CapApp } from "@capacitor/app";
import { StatusBar, Style } from "@capacitor/status-bar";
import { useTheme } from "./ThemeContext";

export default function MobileNavigationHandler() {
  const navigate = useNavigate();
  const location = useLocation();
  const { theme } = useTheme();

  // 1. Android Hardware / Gesture Back Button Handling
  useEffect(() => {
    if (!Capacitor.isNativePlatform()) return;

    let backListener = null;

    const registerBackHandler = async () => {
      try {
        backListener = await CapApp.addListener("backButton", ({ canGoBack }) => {
          // If on root or home page, exit app
          if (location.pathname === "/" || location.pathname === "") {
            CapApp.exitApp();
          } else {
            // Otherwise, navigate back in the React Router stack
            navigate(-1);
          }
        });
      } catch (err) {
        console.warn("Could not register Capacitor backButton listener:", err);
      }
    };

    registerBackHandler();

    return () => {
      if (backListener) {
        backListener.remove();
      }
    };
  }, [location.pathname, navigate]);

  // 2. Mobile Status Bar & Navigation Bar Theming
  useEffect(() => {
    if (!Capacitor.isNativePlatform()) return;

    const syncStatusBar = async () => {
      try {
        const isDark = theme === "dark";
        await StatusBar.setStyle({
          style: isDark ? Style.Dark : Style.Light,
        });
        await StatusBar.setBackgroundColor({
          color: isDark ? "#090d16" : "#f1f5f9",
        });
      } catch (err) {
        console.warn("StatusBar style sync error:", err);
      }
    };

    syncStatusBar();
  }, [theme]);

  // 3. Mark body with native platform class for CSS safe-area tweaks
  useEffect(() => {
    if (Capacitor.isNativePlatform()) {
      document.body.classList.add("is-native-mobile");
    } else {
      document.body.classList.remove("is-native-mobile");
    }
  }, []);

  return null;
}
