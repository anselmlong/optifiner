import Header from '@/components/landing/Header'
import HeroSection from '@/components/landing/HeroSection'
import DemoSection from '@/components/landing/DemoSection'
import FeaturesSection from '@/components/landing/FeaturesSection'
import LinksSection from '@/components/landing/LinksSection'
import CTASection from '@/components/landing/CTASection'
import Footer from '@/components/landing/Footer'

export const Landing = () => {
  return (
    <main className="min-h-screen bg-background text-foreground overflow-x-hidden">
      <Header />
      <HeroSection />
      <DemoSection />
      <FeaturesSection />
      <LinksSection />
      <CTASection />
      <Footer />
    </main>
  )
}
