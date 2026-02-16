# DAC Agent - Pitch Deck Guide

## Overview

This directory contains the investor pitch deck for DAC Agent. The deck is currently in Markdown format for easy editing and version control.

## Files

- `PITCH_DECK.md` - The main pitch deck content (14 slides + 5 appendix slides)
- `PITCH_DECK_README.md` - This file (instructions for using the deck)
- `demo_dashboard.py` - Live demo for presentations

## Deck Structure

### Main Deck (14 Slides)
1. **Cover** - Company name and tagline
2. **The Problem** - "Confused Deputy" attack explanation
3. **Market Validation** - Acuvity acquisition, Sam Altman warnings, OWASP
4. **The Solution** - DAC Agent platform overview
5. **How It Works** - Technical architecture diagram
6. **The Demo** - Interactive dashboard walkthrough
7. **Competitive Landscape** - Positioning vs Acuvity, Cerbos
8. **Why This Matters** - Compliance angle (SOC2, ISO27001, HIPAA)
9. **Business Model** - Pricing, unit economics, revenue streams
10. **Go-to-Market** - ICP, distribution channels, milestones
11. **Traction & Roadmap** - Current status, 12-month plan
12. **Why Now** - Market convergence timing
13. **The Ask** - $2M seed round, use of funds
14. **Closing** - Vision for AI security platform

### Appendix (5 Slides)
- A1: Technical Deep-Dive - Credential exchange flow
- A2: Security Model - Threat model and defense layers
- A3: Open Source Strategy - Licensing and monetization
- A4: Team & Advisors - Founders and hiring plan
- A5: Risks & Mitigations - Risk analysis

## Converting to PowerPoint/PDF

### Option 1: Use Marp (Recommended for Technical Audiences)

```bash
# Install Marp CLI
npm install -g @marp-team/marp-cli

# Convert to PowerPoint
marp PITCH_DECK.md -o PITCH_DECK.pptx

# Convert to PDF
marp PITCH_DECK.md -o PITCH_DECK.pdf

# Convert to HTML (for web presentations)
marp PITCH_DECK.md -o PITCH_DECK.html
```

### Option 2: Use Pandoc (For More Control)

```bash
# Install Pandoc
# macOS: brew install pandoc
# Ubuntu: sudo apt install pandoc

# Convert to PowerPoint
pandoc PITCH_DECK.md -o PITCH_DECK.pptx

# Convert to PDF (requires LaTeX)
pandoc PITCH_DECK.md -o PITCH_DECK.pdf

# Convert with custom template
pandoc PITCH_DECK.md -o PITCH_DECK.pptx --reference-doc=custom-template.pptx
```

### Option 3: Manual (For Visual Polish)

1. **Copy content** from `PITCH_DECK.md`
2. **Paste into:**
   - Google Slides (File → Import slides → Text)
   - PowerPoint (Insert → Text Box)
   - Keynote (Insert → Text)
3. **Add visuals:**
   - Architecture diagrams (use Excalidraw, Figma, or Lucidchart)
   - Screenshots from `demo_dashboard.py`
   - Company logos for competitive analysis
4. **Apply branding:**
   - Company colors
   - Logo on each slide
   - Consistent fonts (recommended: Inter, SF Pro, Helvetica)

## Presenting the Deck

### For Investor Pitches (15 minutes)

**Use slides:** 1-7, 9, 11, 13
**Show demo:** Slides 6 + live demo at http://localhost:3000
**Skip:** Detailed architecture (use appendix for Q&A)
**Focus on:** Problem → Market validation → Solution → Business model → Ask

### For Technical Deep-Dives (45 minutes)

**Use slides:** 1-8, A1-A2
**Show demo:** Live walkthrough with code inspection
**Focus on:** Technical architecture, security model, differentiation

### For Sales Demos (30 minutes)

**Use slides:** 2, 4, 6, 7, 8
**Show demo:** Interactive dashboard with Q&A
**Focus on:** Problem → Solution → How it helps them pass SOC2 audit

## Running the Live Demo

```bash
# Start the interactive dashboard
python demo_dashboard.py

# Open in browser
# http://localhost:3000

# Click "Simulate Attack" to show:
# 1. Alice tries to access Bob's data (prompt injection)
# 2. Sidecar blocks at network layer
# 3. Alice's session revoked
# 4. Bob continues working (zero impact)
```

### Demo Talking Points

1. **Setup (30 sec):** "We have Alice and Bob sharing one agent container. Notice they each have their own token scopes."

2. **Normal flow (30 sec):** "When Alice accesses her own data, everything works normally. You can see the green audit log entry."

3. **Attack (60 sec):** "Now watch what happens when Alice tries prompt injection... [Click button] The sidecar blocks it at the network layer because her token is physically scoped to only her data."

4. **Revocation (30 sec):** "Notice Alice's card turns red - her session is terminated. But Bob's card stays green. He's completely unaffected."

5. **Compliance (30 sec):** "Look at the audit trail. Every entry shows WHO (the user), WHAT (the action), and RESULT. This is what SOC2 auditors want to see."

## Customizing the Deck

### For Different Industries

**Healthcare:**
- Emphasize HIPAA compliance (slide 8)
- Add healthcare-specific examples (patient data access)
- Mention design partners in healthcare AI

**Fintech:**
- Emphasize SOC2/ISO27001 (slide 8)
- Add cost control story ($47K runaway cost)
- Show regulatory risk mitigation

**Enterprise:**
- Emphasize zero-code deployment (slide 4)
- Add Kubernetes/multi-cloud support
- Show integration with existing tools

### For Different Audiences

**VCs:**
- Lead with market validation (Acuvity acquisition)
- Emphasize TAM/SAM/SOM
- Show clear path to Series A

**CISOs:**
- Lead with compliance gap
- Show technical architecture
- Provide security model details

**Developers:**
- Lead with demo
- Show open-source strategy
- Provide code walkthrough

## Key Metrics to Track

Update these numbers in the deck as you progress:

- GitHub stars (currently: target 1,200+)
- Design partners (currently: 3)
- LOIs (currently: 2)
- MRR (target: $150K by Q4 2026)
- Paying customers (target: 50 by Q4 2026)

## Design Assets Needed

To polish the deck, you'll need:

1. **Logo** - Professional logo for DAC Agent
2. **Architecture Diagrams** - Visual versions of ASCII art
3. **Screenshots** - From demo_dashboard.py (take during live demo)
4. **Competitive Matrix** - Visual version of comparison table
5. **Team Photos** - Headshots for team slide
6. **Company Branding** - Color palette, fonts, visual style

### Recommended Tools

- **Diagrams:** Excalidraw (free, open-source)
- **Design:** Figma (free tier available)
- **Screenshots:** CleanShot X (macOS) or ShareX (Windows)
- **Icons:** Heroicons (free)
- **Fonts:** Inter (free, professional)

## Feedback Checklist

Before presenting, review:

- [ ] All metrics are up-to-date
- [ ] Team/advisor info is accurate
- [ ] Contact info is correct
- [ ] Demo works on presentation machine
- [ ] Appendix slides prepared for Q&A
- [ ] Printed backup (in case tech fails)
- [ ] Timing practiced (15 min target)

## Questions You'll Get Asked

**1. "What's your differentiation from Acuvity?"**
→ Use slide 7, emphasize identity vs. policy

**2. "Why can't AWS/GCP just build this?"**
→ Multi-cloud abstraction, developer experience, 18-month head start

**3. "How do you get enterprise customers?"**
→ PLG via open source, land with startups, expand to enterprise

**4. "What's your moat?"**
→ Request-scoped credential exchange (complex distributed systems problem)

**5. "What happens when Proofpoint competes?"**
→ Developer experience they can't match, open source community

**6. "How do you handle multi-cloud?"**
→ Roadmap includes GCP/Azure (Q2 2026), same architecture pattern

**7. "What's your burn rate?"**
→ $150K/mo with current team, $250K/mo after raises

## Next Steps After Pitch

1. **Send follow-up email** within 24 hours
2. **Provide demo access** (cloud-hosted version)
3. **Share technical deep-dive** (appendix slides + GitHub)
4. **Introduce to design partners** (reference customers)
5. **Schedule follow-up call** (answer detailed questions)

---

**Remember:** The best pitch is a conversation, not a presentation. Use the deck as a guide, but be ready to go deep on any topic based on audience interest.
