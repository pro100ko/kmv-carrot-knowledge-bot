
import React from "react";
import MainLayout from "@/layouts/MainLayout";
import HeroSection from "@/components/HeroSection";
import FeatureSection from "@/components/FeatureSection";
import BotPreview from "@/components/BotPreview";
import CodeExample from "@/components/CodeExample";
import FirebaseInfo from "@/components/FirebaseInfo";

const Index = () => {
  return (
    <MainLayout>
      <HeroSection />
      <FeatureSection />
      <BotPreview />
      <CodeExample />
      <FirebaseInfo />
    </MainLayout>
  );
};

export default Index;
