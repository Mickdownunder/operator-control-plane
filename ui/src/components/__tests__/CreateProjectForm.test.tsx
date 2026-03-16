import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { CreateProjectForm } from "../CreateProjectForm";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ refresh: vi.fn(), push: vi.fn() }),
}));

describe("CreateProjectForm", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders form with question textarea and submit", () => {
    render(<CreateProjectForm />);
    expect(screen.getByPlaceholderText(/market size|vertical saas/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /start research/i })).toBeInTheDocument();
  });

  it("shows error when submitting empty question", async () => {
    render(<CreateProjectForm />);
    const submit = screen.getByRole("button", { name: /start research/i });
    fireEvent.click(submit);
    expect(await screen.findByText(/enter a research question/i)).toBeInTheDocument();
  });
});
