"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

interface StatItem {
  name: string;
  value: string;
  change?: string;
  changeType?: "positive" | "negative";
  href?: string;
}

interface StatsCardsWithLinksProps {
  items: StatItem[];
  className?: string;
}

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {}
const Card = React.forwardRef<HTMLDivElement, CardProps>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      data-slot="card"
      className={cn(
        "bg-card text-card-foreground flex flex-col gap-6 rounded-xl border py-6 shadow-sm",
        className
      )}
      {...props}
    />
  )
);
Card.displayName = "Card";

interface CardContentProps extends React.HTMLAttributes<HTMLDivElement> {}
const CardContent = React.forwardRef<HTMLDivElement, CardContentProps>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      data-slot="card-content"
      className={cn("px-6", className)}
      {...props}
    />
  )
);
CardContent.displayName = "CardContent";

interface CardFooterProps extends React.HTMLAttributes<HTMLDivElement> {}
const CardFooter = React.forwardRef<HTMLDivElement, CardFooterProps>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      data-slot="card-footer"
      className={cn("flex items-center px-6 [.border-t]:pt-6", className)}
      {...props}
    />
  )
);
CardFooter.displayName = "CardFooter";

export default function StatsCardsWithLinks({
  items,
  className,
}: StatsCardsWithLinksProps) {
  return (
    <div className={cn("flex items-center justify-center w-full", className)}>
      <dl className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3 w-full">
        {items.map((item) => (
          <Card key={item.name} className="p-0 gap-0">
            <CardContent className="p-6">
              <dd className="flex items-start justify-between space-x-2">
                <span className="truncate text-sm text-muted-foreground">
                  {item.name}
                </span>
                {item.change && item.changeType && (
                  <span
                    className={cn(
                      "text-sm font-medium",
                      item.changeType === "positive"
                        ? "text-emerald-700 dark:text-emerald-500"
                        : "text-red-700 dark:text-red-500"
                    )}
                  >
                    {item.change}
                  </span>
                )}
              </dd>
              <dd className="mt-1 text-3xl font-semibold text-foreground">
                {item.value}
              </dd>
            </CardContent>
            {item.href && (
              <CardFooter className="flex justify-end border-t border-border !p-0">
                <a
                  href={item.href}
                  className="px-6 py-3 text-sm font-medium text-primary hover:text-primary/90"
                >
                  View more →
                </a>
              </CardFooter>
            )}
          </Card>
        ))}
      </dl>
    </div>
  );
}
