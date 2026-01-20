import React from "react";
import { Stack } from "expo-router";
import { View } from "react-native";
import { AuthProvider } from "../src/context/AuthContext";
import { NetworkBanner } from "../src/context/NetworkBanner";

export default function RootLayout() {
  return (
    <AuthProvider>
      <View style={{ flex: 1 }}>
        <NetworkBanner />
        <Stack screenOptions={{ headerShown: false }} />
      </View>
    </AuthProvider>
  );
}
