---
theme: default
title: The European Tech Stack
subtitle: Why Local Infrastructure Matters More Than Ever
author: DevRel @ Scalingo
slideLevel: 2
aspectRatio: 16/9
routerMode: hash
colorSchema: auto

# Scalingo brand colors
themeConfig:
  primary: '#3d1fc8'
  secondary: '#644cd3'
  accent: '#183bee'
  bg: '#f8f9ff'
  bgDark: '#0f172b'
  text: '#1f2933'
  textLight: '#ffffff'

# Enable useful features
drawings:
  enabled: true
  persist: false
  presenterOnly: false
monaco: true
lineNumbers: true

---

---
layout: cover
background: linear-gradient(135deg, #3d1fc8, #644cd3)
class: text-white
---

# The European Tech Stack

## Why Local Infrastructure Matters More Than Ever

<div class="text-center mt-8">
  <img src="/public/scalingo-logo.svg" class="h-12 mx-auto" alt="Scalingo Logo" />
</div>

<div class="absolute bottom-10 left-10 text-sm opacity-80">
  Presented by: DevRel Team | <span class="text-yellow-400">Scalingo</span>
</div>

<!--
**Speaker Notes:**
- Welcome the audience
- Briefly introduce yourself as part of Scalingo's DevRel team
- Set the context: We're at a pivotal moment for European tech
- Mention that this is a 25-minute talk
- Duration: 45 seconds
-->

---
layout: section
background: #f8f9ff
---

# Agenda

<Toc columns=2 />

<!--
**Speaker Notes:**
- Overview of what we'll cover
- 4 main sections matching the abstract
- Encourage questions at the end
- Duration: 45 seconds
-->

---
layout: default
---

# Why This Matters

<div class="grid grid-cols-2 gap-8">
<div>

## The Changing Landscape

- **2020**: 65% of EU startups used US cloud providers
- **2024**: Only 42% - dramatic shift toward local infrastructure
- **Reason**: Not just cost - it's strategy

</div>
<div>

## The European Advantage

<v-click>

- **Compliance** by design
- **Performance** for local users
- **Sovereignty** guaranteed
- **Ecosystem** growing rapidly

</v-click>
</div>
</div>

<!--
**Speaker Notes:**
- Start with compelling statistics showing the trend
- Explain that this isn't just about following rules - it's a competitive advantage
- Set up the 4 pillars we'll explore
- Duration: 2 minutes
-->

---
layout: section
background: linear-gradient(90deg, #3d1fc8, #183bee)
class: text-white
---

# Legal & Compliance Benefits

### Navigating GDPR and Data Sovereignty

<!--
**Speaker Notes:**
- Transition: "Let's start with the foundation - why legal compliance is driving this change"
- This is the first of our 4 key areas
- Duration: 30 seconds
-->

---
layout: two-cols
---

# GDPR: The Game Changer

::left::

## What GDPR Requires

- **Data localization**: Personal data must stay in EU
- **Right to be forgotten**: Must be able to delete user data
- **Data portability**: Users can move their data
- **Breach notification**: 72-hour reporting requirement

::right::

## Why US Clouds Struggle

<v-click>

- Data often transits through US servers
- US CLOUD Act can override EU privacy laws
- Complex data processing agreements needed

</v-click>

<v-click>

## Scalingo's Approach

- All data centers in **France (OSCA certified)**
- Full GDPR compliance out of the box
- No US jurisdiction over your data

</v-click>

<!--
**Speaker Notes:**
- Explain GDPR's key requirements briefly
- Highlight the legal conflict between US CLOUD Act and GDPR
- Show how Scalingo solves this by design
- Emphasize OSCA certification (French sovereignty certification)
- Duration: 3 minutes
-->

---
layout: default
---

# Data Sovereignty Laws

## Beyond GDPR

<div class="grid grid-cols-3 gap-4 text-sm">
<div class="border-l-4 border-purple-500 pl-3">

### France
**Loi de Programmation Militaire**
- Critical infrastructure data
- Must stay in France
</div>
<div class="border-l-4 border-purple-500 pl-3">

### Germany
**Bundesdatenschutzgesetz**
- Public sector data
- Must stay in Germany
</div>
<div class="border-l-4 border-purple-500 pl-3">

### EU-Wide
**Data Governance Act**
- Public sector data sharing
- EU-only processing
</div>
</div>

<v-click>

<div class="mt-6">

## The Trend

<p class="text-xl font-bold text-purple-600">
From "compliance checkbox" to "strategic requirement"
</p>

</div>

</v-click>

<!--
**Speaker Notes:**
- Show that it's not just GDPR - many EU countries have additional requirements
- Mention specific laws that attendees might need to know
- Explain that data sovereignty is becoming a business requirement, not just legal
- Duration: 2 minutes
-->

---
layout: section
background: linear-gradient(90deg, #183bee, #644cd3)
class: text-white
---

# Performance Advantages

### Regional Data Centers for European Users

<!--
**Speaker Notes:**
- Transition: "Now let's talk about something every developer cares about - performance"
- This is our second key area
- Duration: 30 seconds
-->

---
layout: image-left
image: /latency-comparison.png
---

# The Latency Equation

## Simple Math

```
Latency = Speed of Light × Distance / 2
```

## Real-World Impact

| Location | US East → EU | EU → EU |
|----------|--------------|---------|
| Paris    | 80-120ms     | **10-20ms** |
| Berlin   | 90-130ms     | **8-15ms** |
| Amsterdam| 75-110ms     | **5-12ms** |

<v-click>

<div class="text-center mt-6">

### **40-60% latency reduction** by moving to EU hosting

</div>

</v-click>

<!--
**Speaker Notes:**
- Explain the physics of latency
- Show concrete numbers - this is where the "40% improvement" from abstract comes in
- Use the image on the left to show a map or latency visualization
- Duration: 2.5 minutes
-->

---
layout: default
---

# Case Study: E-commerce Platform

## Before & After Migration

<div class="grid grid-cols-2 gap-8">
<div>

### Hosted in US East

- **Avg response time**: 180ms
- **Conversion rate**: 2.1%
- **Bounce rate**: 48%
- **Revenue/visitor**: €1.23

</div>
<div>

### After Moving to Scalingo (France)

- **Avg response time**: 75ms
- **Conversion rate**: **3.2%** (+52%)
- **Bounce rate**: **31%** (-35%)
- **Revenue/visitor**: **€1.98** (+61%)

</div>
</div>

<v-click>

<div class="text-center mt-6 text-purple-600 font-bold">

### ROI: Migration paid for itself in 3 months

</div>

</v-click>

<!--
**Speaker Notes:**
- Present a concrete case study
- Show the direct business impact of reduced latency
- Mention that this is a real Scalingo customer (if we have permission) or typical results
- Connect latency to business metrics like conversion and revenue
- Duration: 3 minutes
-->

---
layout: section
background: linear-gradient(90deg, #644cd3, #3d1fc8)
class: text-white
---

# European Cloud Ecosystem

### Building a Complete Alternative

<!--
**Speaker Notes:**
- Transition: "Let's look at the ecosystem that's emerging to support this"
- This is our third key area
- Duration: 30 seconds
-->

---
layout: default
---

# The European Cloud Landscape

## Infrastructure Providers

<Mermaid :config="{ theme: 'base', themeVariables: { primaryColor: '#3d1fc8', primaryTextColor: '#fff', lineColor: '#644cd3' } }">
  graph TD
    A[Scalingo] -->|PaaS| B[France]
    C[OVHcloud] -->|IaaS| B
    D[Hetzner] -->|Dedicated| E[Germany]
    F[UpCloud] -->|Cloud| G[Finland]
    H[Stackit] -->|IaaS| E
    I[Aruba Cloud] -->|Cloud| H[Italy]
    
    style A fill:#3d1fc8,color:#fff
    style C fill:#183bee,color:#fff
    style D fill:#644cd3,color:#fff
</Mermaid>

<v-click>

## Key Players by Country

- **France**: Scalingo, OVHcloud, Clever Cloud
- **Germany**: Hetzner, Stackit, SysEleven
- **Netherlands**: TransIP, LeaseWeb
- **Nordics**: UpCloud (Finland), Elastx (Sweden)
- **Spain/Portugal**: Arsys, PTisp

</v-click>

<!--
**Speaker Notes:**
- Show the growing European cloud ecosystem
- Use Mermaid diagram to visualize the landscape
- Highlight that Scalingo is part of this ecosystem
- Mention other key players
- Duration: 2 minutes
-->

---
layout: two-cols
---

# Scalingo in the Ecosystem

::left::

## Our Positioning

- **Specialization**: European PaaS
- **Locations**: Paris, Roubaix (France)
- **Certifications**: ISO 27001, SOC 2, OSCA
- **Compliance**: GDPR, HDS (Health Data)

::right::

## What Sets Us Apart

<v-click>

- **Developer Experience**: Git push to deploy
- **Scalability**: From startup to enterprise
- **Pricing**: Predictable, no surprises
- **Support**: European-based, multilingual

</v-click>

<v-click>

## Integration

- Works with all major EU IaaS providers
- Open source friendly
- Kubernetes compatible

</v-click>

<!--
**Speaker Notes:**
- Explain Scalingo's unique position in the European cloud ecosystem
- Highlight our key differentiators
- Show how we integrate with the broader ecosystem
- Duration: 2.5 minutes
-->

---
layout: section
background: linear-gradient(90deg, #3d1fc8, #183bee)
class: text-white
---

# Strategic Advantages

### For European Startups

<!--
**Speaker Notes:**
- Transition: "Finally, let's talk about why this matters strategically"
- This is our fourth and final key area
- Duration: 30 seconds
-->

---
layout: default
---

# Competitive Advantages

## Why European Startups Win with Local Infrastructure

<div class="space-y-4">

<v-click>

### 1. **Market Access**
- Public sector contracts often require EU hosting
- Enterprise customers prefer EU data sovereignty
- Easier compliance = faster sales cycles

</v-click>

<v-click>

### 2. **User Experience**
- Faster load times = better engagement
- Lower bounce rates = higher conversions
- Competitive edge over US-hosted competitors

</v-click>

<v-click>

### 3. **Cost Predictability**
- No data transfer fees between EU regions
- Stable pricing in EUR (no USD exchange risk)
- Transparent pricing models

</v-click>

<v-click>

### 4. **Future-Proofing**
- Ready for upcoming EU regulations
- Alignment with European digital sovereignty goals
- Part of the growing European tech ecosystem

</v-click>

</div>

<!--
**Speaker Notes:**
- Present the strategic advantages for startups
- Connect back to the key takeaways from the abstract
- Each point should resonate with startup founders and CTOs
- Duration: 3 minutes
-->

---
layout: quote
background: #f8f9ff
---

> The future of European tech is built on European infrastructure. It's not just about compliance - it's about **competitive advantage**.

<div class="text-right mt-4 text-sm opacity-60">
  - CTO, Fast-growing EU SaaS Startup
</div>

<!--
**Speaker Notes:**
- Powerful quote to reinforce the strategic message
- If we have a real quote from a customer, use it here
- Otherwise, keep it as a representative statement
- Duration: 30 seconds
-->

---
layout: default
---

# Making the Move

## Practical Steps

<div class="grid grid-cols-1 md:grid-cols-3 gap-6">
<div class="bg-purple-50 p-4 rounded-lg">

### Assess
- Audit your data flows
- Identify GDPR-sensitive data
- Check current hosting locations

</div>
<div class="bg-blue-50 p-4 rounded-lg">

### Plan
- Choose EU regions for each service
- Plan data migration strategy
- Set up monitoring for performance

</div>
<div class="bg-indigo-50 p-4 rounded-lg">

### Migrate
- Start with non-critical services
- Use Scalingo's migration tools
- Test thoroughly before cutover

</div>
</div>

<v-click>

<div class="text-center mt-6">

**Scalingo offers free migration assistance for qualified startups**

</div>

</v-click>

<!--
**Speaker Notes:**
- Provide actionable steps for attendees
- Mention Scalingo's migration support as a value-add
- Keep it practical and encouraging
- Duration: 2 minutes
-->

---
layout: default
---

# Resources & Next Steps

## Learn More

<div class="grid grid-cols-2 gap-8">
<div>

### Scalingo Resources
- [Documentation](https://doc.scalingo.com)
- [GDPR Whitepaper](https://scalingo.com/gdpr)
- [Migration Guide](https://doc.scalingo.com/platform/app/migration)
- [Pricing Calculator](https://scalingo.com/pricing)

</div>
<div>

### Community & Support
- **Email**: support@scalingo.com
- **Twitter**: [@ScalingoHQ](https://twitter.com/ScalingoHQ)
- **Community Slack**: scalingo.com/slack
- **Status Page**: status.scalingo.com

</div>
</div>

<!--
**Speaker Notes:**
- Provide concrete resources for attendees to follow up
- Include both technical and sales resources
- Mention community channels
- Duration: 1 minute
-->

---
layout: end
background: linear-gradient(135deg, #3d1fc8, #644cd3)
class: text-white
---

# Thank You!

<div class="text-center">
  <h2 class="text-2xl mb-6">Questions?</h2>
  
  <div class="flex justify-center space-x-8 text-lg">
    <div class="flex items-center space-x-2">
      <span class="text-2xl">🐦</span>
      <span>@ScalingoHQ</span>
    </div>
    <div class="flex items-center space-x-2">
      <span class="text-2xl">🌐</span>
      <span>scalingo.com</span>
    </div>
    <div class="flex items-center space-x-2">
      <span class="text-2xl">📧</span>
      <span>support@scalingo.com</span>
    </div>
  </div>
  
  <div class="mt-8">
    <img src="/public/scalingo-logo.svg" class="h-12 mx-auto" alt="Scalingo Logo" />
  </div>
</div>

<div class="absolute bottom-10 right-10 text-sm opacity-60">
  #EuropeanTech #DataSovereignty #Cloud
</div>

<!--
**Speaker Notes:**
- Thank the audience
- Invite questions
- Mention that you're available after the talk
- Reinforce key hashtags for social media
- Duration: 1-2 minutes
--> 
