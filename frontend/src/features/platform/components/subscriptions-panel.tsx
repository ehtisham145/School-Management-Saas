"use client";

import { useState } from "react";
import { Plus } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Modal } from "@/components/ui/modal";
import { Select } from "@/components/ui/select";
import { Table, TableCell, TableHead, TableHeaderCell, TableRow } from "@/components/ui/table";
import { Textarea } from "@/components/ui/textarea";
import {
  optional,
  optionalMoney,
  requiredChoice,
  requiredDate,
  sanitizeMoney,
  todayInRiyadh,
  useValidatedForm,
} from "@/lib/use-validated-form";
import {
  activateSubscription,
  expireSubscription,
  getFormChoices,
  getSubscriptionCounts,
  listSubscriptions,
} from "../api";
import {
  BILLING_CYCLES,
  SUBSCRIPTION_STATUSES,
  type BillingCycle,
  type FormChoices,
  type Subscription,
  type SubscriptionStatus,
} from "../schemas";
import { useLoad } from "../use-load";
import {
  ConfirmDialog,
  DayWithHijri,
  FilterTabs,
  LoadFeedback,
  localName,
  Money,
  Notice,
  PageHeader,
  Pagination,
  SearchBox,
  SubscriptionStatusBadge,
} from "./panel-ui";

const ALL = "all";
type StatusFilter = SubscriptionStatus | typeof ALL;

function ActivateDialog({
  choices,
  onClose,
  onSaved,
}: {
  choices: FormChoices;
  onClose: () => void;
  onSaved: () => void;
}) {
  const t = useTranslations("Platform.subscriptions");
  const tCommon = useTranslations("Platform.common");
  const locale = useLocale();

  const form = useValidatedForm({
    initial: {
      school: "",
      plan: "",
      billing_cycle: "monthly",
      starts_on: todayInRiyadh(),
      price: "",
      notes: "",
    },
    validators: {
      school: requiredChoice,
      plan: requiredChoice,
      starts_on: requiredDate,
      price: optionalMoney,
      notes: optional(1000),
    },
    sanitizers: { price: sanitizeMoney },
    rejectedInputErrors: { price: "moneyCharacters" },
    validateWhileTyping: true,
    idPrefix: "subscription-",
    submit: async (values) => {
      await activateSubscription({
        school: Number(values.school),
        plan: Number(values.plan),
        billing_cycle: values.billing_cycle as BillingCycle,
        starts_on: values.starts_on,
        price: values.price || null,
        notes: values.notes.trim(),
      });
    },
    describeFieldError: (name) => (name === "school" ? t("form.schoolTaken") : null),
    onSuccess: onSaved,
  });

  const plan = choices.plans.find((option) => String(option.id) === form.values.plan);
  const listPrice =
    plan && (form.values.billing_cycle === "yearly" ? plan.yearly_price : plan.monthly_price);

  return (
    <Modal
      open
      onClose={onClose}
      title={t("form.title")}
      description={t("form.description")}
      closeLabel={tCommon("close")}
    >
      <form onSubmit={form.handleSubmit} noValidate className="grid gap-3 sm:grid-cols-2">
        <div className="sm:col-span-2">
          <Field
            id="subscription-school"
            label={t("form.school")}
            required
            error={form.errorFor("school")}
          >
            <Select {...form.bind("school")} className="h-11">
              <option value="">{tCommon("choose")}</option>
              {choices.schools.map((school) => (
                <option key={school.id} value={school.id}>
                  {localName(school, locale)} ({school.code})
                </option>
              ))}
            </Select>
          </Field>
        </div>
        <Field id="subscription-plan" label={t("form.plan")} required error={form.errorFor("plan")}>
          <Select {...form.bind("plan")} className="h-11">
            <option value="">{tCommon("choose")}</option>
            {choices.plans.map((option) => (
              <option key={option.id} value={option.id}>
                {localName(option, locale)}
              </option>
            ))}
          </Select>
        </Field>
        <Field id="subscription-billing_cycle" label={t("form.billingCycle")} required>
          <Select {...form.bind("billing_cycle")} className="h-11">
            {BILLING_CYCLES.map((cycle) => (
              <option key={cycle} value={cycle}>
                {tCommon(`cycles.${cycle}`)}
              </option>
            ))}
          </Select>
        </Field>
        <Field
          id="subscription-starts_on"
          label={t("form.startsOn")}
          required
          hint={t("form.startsOnHint")}
          error={form.errorFor("starts_on")}
        >
          <Input {...form.bind("starts_on")} type="date" className="h-11" />
        </Field>
        <Field
          id="subscription-price"
          label={t("form.price")}
          hint={
            listPrice
              ? t("form.priceHint", { price: Number(listPrice).toLocaleString(locale) })
              : t("form.priceHintNoPlan")
          }
          error={form.errorFor("price")}
        >
          <Input
            {...form.bind("price")}
            inputMode="decimal"
            dir="ltr"
            placeholder={listPrice ?? ""}
            className="h-11"
          />
        </Field>
        <div className="sm:col-span-2">
          <Field id="subscription-notes" label={t("form.notes")} error={form.errorFor("notes")}>
            <Textarea {...form.bind("notes")} rows={2} />
          </Field>
        </div>

        {choices.schools.length === 0 || choices.plans.length === 0 ? (
          <p
            role="alert"
            className="rounded-control bg-amber-50 p-3 text-sm text-amber-800 sm:col-span-2"
          >
            {choices.plans.length === 0 ? t("form.noPlans") : t("form.noSchools")}
          </p>
        ) : null}

        {form.formError && (
          <p
            role="alert"
            className="rounded-control bg-red-50 p-3 text-sm text-red-800 sm:col-span-2"
          >
            {form.formError}
          </p>
        )}

        <div className="flex justify-end gap-2 sm:col-span-2">
          <Button type="button" variant="ghost" size="sm" onClick={onClose}>
            {tCommon("cancel")}
          </Button>
          <Button type="submit" size="sm" loading={form.saving}>
            {form.saving ? tCommon("saving") : t("form.submit")}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

export function SubscriptionsPanel() {
  const t = useTranslations("Platform.subscriptions");
  const tCommon = useTranslations("Platform.common");
  const locale = useLocale();

  const [query, setQuery] = useState({ page: 1, search: "", status: ALL as StatusFilter });
  const [activating, setActivating] = useState(false);
  const [expiring, setExpiring] = useState<Subscription | null>(null);
  const [notice, setNotice] = useState<"activated" | "expired" | null>(null);

  const list = useLoad(
    (signal) =>
      listSubscriptions(
        {
          page: query.page,
          search: query.search,
          status: query.status === ALL ? undefined : query.status,
        },
        signal,
      ),
    JSON.stringify(query),
  );
  const counts = useLoad(getSubscriptionCounts, "counts");
  const choices = useLoad(getFormChoices, "choices");
  const summary = counts.state.name === "ready" ? counts.state.data : null;

  function refresh(next: "activated" | "expired") {
    setActivating(false);
    setExpiring(null);
    setNotice(next);
    list.reload();
    counts.reload();
  }

  const isFiltered = query.search !== "" || query.status !== ALL;

  return (
    <>
      <PageHeader
        title={t("title")}
        subtitle={t("subtitle")}
        action={
          <Button
            size="sm"
            disabled={choices.state.name !== "ready"}
            onClick={() => {
              setNotice(null);
              setActivating(true);
            }}
          >
            <Plus aria-hidden="true" />
            {t("activate")}
          </Button>
        }
      />

      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <FilterTabs<StatusFilter>
          label={t("columns.status")}
          value={query.status}
          onChange={(status) => setQuery((current) => ({ ...current, status, page: 1 }))}
          options={[
            { value: ALL, label: t("all"), count: summary?.total },
            ...SUBSCRIPTION_STATUSES.map((status) => ({
              value: status,
              label: t(`status.${status}`),
              count: summary?.[status],
            })),
          ]}
        />
        <SearchBox
          label={t("searchLabel")}
          onSearch={(search) => setQuery((current) => ({ ...current, search, page: 1 }))}
        />
      </div>

      {notice && <Notice tone="success">{t(`notices.${notice}`)}</Notice>}

      <LoadFeedback state={list.state} onRetry={list.reload} />

      {list.state.name === "ready" && list.state.data.count === 0 && (
        <EmptyState
          title={isFiltered ? t("noResults") : t("empty")}
          description={isFiltered ? undefined : t("emptyDescription")}
        />
      )}

      {list.state.name === "ready" && list.state.data.count > 0 && (
        <>
          <Table className="bg-bg">
            <TableHead>
              <TableRow>
                <TableHeaderCell>{t("columns.school")}</TableHeaderCell>
                <TableHeaderCell>{t("columns.plan")}</TableHeaderCell>
                <TableHeaderCell>{t("columns.price")}</TableHeaderCell>
                <TableHeaderCell>{t("columns.startsOn")}</TableHeaderCell>
                <TableHeaderCell>{t("columns.endsOn")}</TableHeaderCell>
                <TableHeaderCell>{t("columns.status")}</TableHeaderCell>
                <TableHeaderCell>{tCommon("actions")}</TableHeaderCell>
              </TableRow>
            </TableHead>
            <tbody>
              {list.state.data.results.map((subscription) => (
                <TableRow key={subscription.id}>
                  <TableCell>
                    <span className="block font-semibold text-ink">
                      <bdi>{localName(subscription.school, locale)}</bdi>
                    </span>
                    <span className="block text-xs text-ink-soft" dir="ltr">
                      {subscription.school.code}
                    </span>
                  </TableCell>
                  <TableCell>{localName(subscription.plan, locale)}</TableCell>
                  <TableCell>
                    <Money value={subscription.price} locale={locale} />
                    <span className="block text-xs text-ink-soft">
                      {tCommon(`cycles.${subscription.billing_cycle}`)}
                    </span>
                  </TableCell>
                  <TableCell>
                    <DayWithHijri value={subscription.starts_on} locale={locale} />
                  </TableCell>
                  <TableCell>
                    <DayWithHijri value={subscription.ends_on} locale={locale} />
                  </TableCell>
                  <TableCell>
                    <SubscriptionStatusBadge status={subscription.status} />
                  </TableCell>
                  <TableCell>
                    {subscription.status === "active" ? (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => {
                          setNotice(null);
                          setExpiring(subscription);
                        }}
                      >
                        {t("expire")}
                      </Button>
                    ) : (
                      <span className="text-ink-soft">-</span>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </tbody>
          </Table>
          <Pagination
            page={query.page}
            count={list.state.data.count}
            onPage={(page) => setQuery((current) => ({ ...current, page }))}
          />
        </>
      )}

      {activating && choices.state.name === "ready" && (
        <ActivateDialog
          choices={choices.state.data}
          onClose={() => setActivating(false)}
          onSaved={() => refresh("activated")}
        />
      )}

      {expiring && (
        <ConfirmDialog
          title={t("confirmExpire.title", { school: localName(expiring.school, locale) })}
          description={t("confirmExpire.body")}
          confirmLabel={t("expire")}
          destructive
          onClose={() => setExpiring(null)}
          onConfirm={async () => {
            await expireSubscription(expiring.id);
            refresh("expired");
          }}
        />
      )}
    </>
  );
}
