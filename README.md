# AIDE — Archive · Identify · Determine · Export

AIDE is a standalone local tool built around a simple idea:

> **Give people a clear view of a project, let them decide what matters, and provide a controlled way to represent it.**

AIDE can be used to inspect, understand, compare, document, and export projects in a form that is easier to read, share, preserve, or work with elsewhere.

It can also be used to prepare project material for external AI tools, but AI is not what defines AIDE.

---

## The Idea

Projects become difficult to understand as they grow.

Files are added, folders change, configuration accumulates, old material remains, and eventually it can become surprisingly difficult to answer a simple question:

**What is actually in this project?**

AIDE is an attempt to make that question easier to answer.

The concept can be expressed as:

**See it → Choose it → Inspect it → Protect it → Export it**

### See it

AIDE gives a project a visible structure instead of treating it as an anonymous collection of files.

The purpose is to make the project easier to understand as a whole.

### Choose it

Not everything in a project necessarily belongs in every representation of it.

AIDE lets the user decide what should be included and what should remain outside the export.

### Inspect it

Before anything is exported, the selected material can be reviewed.

The intention is to make the resulting representation something the user understands and controls, rather than something produced blindly.

### Protect it

Projects can contain information that should not accidentally leave the local environment.

AIDE identifies potentially sensitive material and keeps it out of exports by default.

It also avoids exposing the original local filesystem path in exported project representations.

### Export it

Once the project has been understood and the desired material selected, AIDE can turn it into a portable representation.

That representation can become documentation, a project snapshot, something to compare against later, or material for another tool.

---

## Why AIDE Exists

AIDE was created from a practical need:

**to make projects easier to see and work with before handing their contents to something else.**

That "something else" might be another person, an archive, a document, a development workflow, or an AI tool.

The important part is that the export is not the starting point.

**Understanding and control come first.**

AIDE therefore does not try to decide what a project means.

**AIDE provides the tools to identify, determine, and represent it. The person using it decides what that representation should contain.**

---

## Local by Design

AIDE works locally and does not require an internet connection or an external AI service.

This is intentional.

A project can be scanned, inspected, selected, and represented without first sending its contents somewhere else.

What happens with the resulting export is then up to the person using AIDE.

---

## What AIDE Does

At its core, AIDE can:

* scan project directories and their contents
* present project structure in a human-readable way
* identify different types of files and potentially sensitive material
* let the user determine what is included
* preview the selected material
* create portable project representations
* create structured file trees and metadata
* produce exports suitable for documentation or external tools

The exact capabilities and implementation can evolve over time.

The underlying idea remains the same:

> **Understand what you have. Decide what matters. Then represent it.**

---

## AIDE and AI

AIDE is **not an AI application**.

AI is simply one possible destination for information produced by AIDE.

For example, a project can be represented as structured text and supplied to an external AI tool for discussion, analysis, coding assistance, or documentation work.

But the same representation can be used entirely without AI.

AIDE is about the project and the person's control over its representation — not about the tool receiving that representation.

---

## Open Source

AIDE is released as open source as part of my wider ecosystem.

The source is available for others to inspect, use, learn from, modify, adapt, and build upon.

The implementation is one expression of the concept, not a prescription for how the concept must be used.

The project can evolve in directions I did not originally anticipate.

That is part of what open source makes possible.

---

## Where to Find AIDE

The **source code** is available in this repository.

A packaged **Windows executable** is available as a ZIP archive through the project's **Releases**.

The source and the released executable represent the same project from two different perspectives:

**one for those who want to use it, and one for those who want to look inside.**

For technical details about the implementation, see `AIDE Code.md`.

---

## My Perspective (the real READ  ME)

I use a **cross-platform AI methodology**, working across multiple AI platforms and tools and using each where it adds value.

**My workflow is human-led and AI-augmented.** I use AI and other tools for ideas, research, coding, testing, documentation, visual work, or whatever a project requires.

My methodology demonstrates that meaningful development is possible using **unpaid AI tools**. Paid tools are neither required nor excluded.

**My projects are examples of what I have been able to create from this perspective, not a prescription for how others should work.**

I release my projects as **open source as part of my ecosystem**, making them and their development approach available for others to explore, use, learn from, or develop further. Open source is part of my ecosystem, not a requirement for anyone else using or building upon my work.

Just as importantly, I want this approach to encourage people to **try their own creativity without feeling pressured to achieve a particular result**. You might want to write code, paint, make music, build something, or simply experiment. If it is interesting and enjoyable, that can be reason enough to start.

**The purpose is not to prescribe a way of working, but to demonstrate what was made possible from this perspective.**

---

## 📄 License

This project is licensed under the MIT License.

**A note about the project:**
Open source is part of my ecosystem. This project is shared openly so that others can use it, inspect it, modify it, learn from it, and build upon it.

**A note about the methodology:**
This project is an example of what I have created from my own perspective and methodology. You are free to use it in your own way; my approach is not a requirement for using or building upon this project.

The full MIT License is reproduced below:

```text
Copyright (c) 2026 TheHuManInTheMiddle

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation fil
```
