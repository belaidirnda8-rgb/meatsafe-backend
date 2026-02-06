import React from "react";
import { Tabs } from "expo-router";
import { useAuth } from "../../src/context/AuthContext";
import { Text, TouchableOpacity, View } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { colors } from "../../src/theme";

function LogoutButton() {
  const { logout } = useAuth();

  const handleLogout = async () => {
    await logout();
  };

  return (
    <TouchableOpacity
      onPress={handleLogout}
      style={{ marginRight: 12 }}
      hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
    >
      <View style={{ flexDirection: "row", alignItems: "center" }}>
        <Ionicons
          name="log-out-outline"
          size={20}
          color={colors.primary}
          style={{ marginRight: 4 }}
        />
        <Text style={{ color: colors.primary, fontWeight: "600" }}>Déconnexion</Text>
      </View>
    </TouchableOpacity>
  );
}

export default function AppLayout() {
  const { user } = useAuth();

  if (!user) {
    return <Text>Non authentifié</Text>;
  }

  if (user.role === "inspector") {
    return (
      <Tabs
        screenOptions={{
          headerShown: true,
          headerRight: () => <LogoutButton />,
          tabBarActiveTintColor: colors.primary,
          tabBarInactiveTintColor: colors.textMuted,
        }}
      >
        <Tabs.Screen
          name="inspector/index"
          options={{
            title: "Mes saisies",
            headerTitle: "Mes saisies",
            tabBarLabel: "Mes saisies",
            tabBarIcon: ({ color, size }) => (
              <Ionicons name="list-outline" size={size} color={color} />
            ),
          }}
        />
        <Tabs.Screen
          name="inspector/new"
          options={{
            title: "Nouvelle saisie",
            headerTitle: "Nouvelle saisie",
            tabBarLabel: "Nouvelle saisie",
            tabBarIcon: ({ color, size }) => (
              <Ionicons name="add-circle-outline" size={size} color={color} />
            ),
          }}
        />
      </Tabs>
    );
  }

  // Admin
  return (
    <Tabs
      screenOptions={{
        headerShown: true,
        headerRight: () => <LogoutButton />,
        tabBarActiveTintColor: colors.primary,
        tabBarInactiveTintColor: colors.textMuted,
      }}
    >
      <Tabs.Screen
        name="admin/index"
        options={{
          title: "Tableau de bord",
          headerTitle: "Tableau de bord",
          tabBarLabel: "Dashboard",
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="speedometer-outline" size={size} color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="admin/seizures"
        options={{
          title: "Saisies",
          headerTitle: "Saisies",
          tabBarLabel: "Saisies",
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="list-outline" size={size} color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="admin/slaughterhouses"
        options={{
          title: "Abattoirs",
          headerTitle: "Abattoirs",
          tabBarLabel: "Abattoirs",
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="business-outline" size={size} color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="admin/inspectors"
        options={{
          title: "Inspecteurs",
          headerTitle: "Inspecteurs",
          tabBarLabel: "Inspecteurs",
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="people-outline" size={size} color={color} />
          ),
        }}
      />
    </Tabs>
  );
}
