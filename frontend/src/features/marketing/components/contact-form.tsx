"use client";

import { useState, type FormEvent } from "react";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { CONTACT_EMAIL } from "../contact-info";

type ContactFormProps = {
  planLabel?: string;
};

export function ContactForm({ planLabel }: ContactFormProps) {
  const t = useTranslations("Marketing.contact.form");
  const [name, setName] = useState("");
  const [school, setSchool] = useState("");
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState("");

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const subject = planLabel ? `Schoolify demo request — ${planLabel}` : "Schoolify demo request";
    const bodyLines = [
      `Name: ${name}`,
      `School: ${school}`,
      `Email: ${email}`,
      ...(planLabel ? [`Plan: ${planLabel}`] : []),
      "",
      message,
    ];

    const mailto = `mailto:${CONTACT_EMAIL}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(bodyLines.join("\n"))}`;
    window.location.href = mailto;
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4">
      {planLabel && (
        <p className="border border-[var(--mk-line-strong)] bg-accent px-3.5 py-2 text-sm text-accent-foreground">
          {t("planNote", { plan: planLabel })}
        </p>
      )}

      <div className="grid gap-4 sm:grid-cols-2">
        <div className="flex flex-col gap-1.5">
          <label htmlFor="contact-name" className="text-sm font-medium text-foreground">
            {t("nameLabel")}
          </label>
          <Input
            id="contact-name"
            name="name"
            required
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder={t("namePlaceholder")}
          />
        </div>
        <div className="flex flex-col gap-1.5">
          <label htmlFor="contact-school" className="text-sm font-medium text-foreground">
            {t("schoolLabel")}
          </label>
          <Input
            id="contact-school"
            name="school"
            required
            value={school}
            onChange={(event) => setSchool(event.target.value)}
            placeholder={t("schoolPlaceholder")}
          />
        </div>
      </div>

      <div className="flex flex-col gap-1.5">
        <label htmlFor="contact-email" className="text-sm font-medium text-foreground">
          {t("emailLabel")}
        </label>
        <Input
          id="contact-email"
          name="email"
          type="email"
          required
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          placeholder={t("emailPlaceholder")}
        />
      </div>

      <div className="flex flex-col gap-1.5">
        <label htmlFor="contact-message" className="text-sm font-medium text-foreground">
          {t("messageLabel")}
        </label>
        <textarea
          id="contact-message"
          name="message"
          required
          rows={5}
          value={message}
          onChange={(event) => setMessage(event.target.value)}
          placeholder={t("messagePlaceholder")}
          className="w-full rounded-[var(--radius)] border border-input bg-transparent px-3 py-2 text-sm shadow-xs outline-none placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
        />
      </div>

      <Button type="submit" size="lg" className="w-fit">
        {t("submit")}
      </Button>
    </form>
  );
}
