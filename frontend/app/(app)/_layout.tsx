import React from "react";
import { Tabs } from "expo-router";
import { useAuth } from "../../src/context/AuthContext";
import { Text } from "react-native";

export default function AppLayout() {
  const { user } = useAuth();

  if (!user) {
    return <Text>Non authentifié</Text>;
  }

  if (user.role === "inspector") {
    return (
      <Tabs screenOptions={{ headerShown: true }}>
        <Tabs.Screen
          name="inspector/index"
          options={{ title: "Mes saisies", headerTitle: "Mes saisies" }}
        />
        <Tabs.Screen
          name="inspector/new"
          options={{ title: "Nouvelle saisie", headerTitle: "Nouvelle saisie" }}
        />
      </Tabs>
    );
  }

  // Admin
  return (
    <Tabs screenOptions={{ headerShown: true }}>
      <Tabs.Screen
        name="admin/index"
        options={{ title: "Tableau de bord", headerTitle: "Tableau de bord" }}
      />
      <Tabs.Screen
        name="admin/seizures"
        options={{ title: "Saisies", headerTitle: "Saisies" }}
      />
      <Tabs.Screen
        name="admin/slaughterhouses"
        options={{ title: "Abattoirs", headerTitle: "Abattoirs" }}
      />
      <Tabs.Screen
        name="admin/inspectors"
        options={{ title: "Inspecteurs", headerTitle: "Inspecteurs" }}
      />
    </Tabs>
  );
}
