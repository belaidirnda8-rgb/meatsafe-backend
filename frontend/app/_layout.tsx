import React from "react";
import { Stack } from "expo-router";
import { View } from "react-native";
import { AuthProvider } from "../src/context/AuthContext";
import { NetworkBanner } from "../src/context/NetworkBanner";
import { OfflineQueueProvider } from "../src/store/offlineQueue";

export default function RootLayout() {
  return (
    <AuthProvider>
      <OfflineQueueProvider>
        <View style={{ flex: 1 }}>
          <NetworkBanner />
          <Stack screenOptions={{ headerShown: false }} />
        </View>
      </OfflineQueueProvider>
    </AuthProvider>
  );
}
