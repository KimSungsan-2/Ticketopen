"""메일 발송"""
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import date
from config import SMTP_EMAIL, SMTP_PASSWORD, NOTIFY_EMAIL

logger = logging.getLogger(__name__)


def build_report(
    new_items: list[dict],
    unregistered_performances: list[dict],
    unregistered_seasons: list[dict],
    parse_failures: list[dict],
    match_failures: list[dict],
    duplicates: list[dict],
    kids_excluded: list[dict],
) -> str:
    """메일 본문 생성"""
    today = date.today().strftime("%Y-%m-%d")
    lines = [f"[NOL 티켓 오픈 알림] {today}", ""]

    # 신규 발견
    if new_items:
        lines.append(f"■ 신규 발견 {len(new_items)}건 (등록 가능):")
        for i, item in enumerate(new_items, 1):
            lines.append(
                f"{i}. {item['공연명']} | {item['기타']} | "
                f"{item['오픈날짜']} {item['오픈시간']} | {item['오픈회차']}"
            )
        lines.append("")

    # podor 미등록 공연
    if unregistered_performances:
        lines.append(f"■ podor 미등록 공연 {len(unregistered_performances)}건 (공연정보 자체가 없음):")
        for item in unregistered_performances:
            lines.append(f"- \"{item['raw_title']}\" — podor에 공연 등록 필요")
        lines.append("")

    # 시즌 미등록
    if unregistered_seasons:
        lines.append(f"■ 시즌 미등록 {len(unregistered_seasons)}건 (공연은 있으나 해당 시즌 없음):")
        for item in unregistered_seasons:
            lines.append(
                f"- \"{item['공연명']}\" — 전체공연기간 {item.get('period_start', '?')}~{item.get('period_end', '?')}에 해당하는 시즌 없음"
            )
        lines.append("")

    # 파싱 실패
    if parse_failures:
        lines.append(f"■ 파싱 실패 {len(parse_failures)}건 (티켓오픈 정보 추출 불가):")
        for item in parse_failures:
            lines.append(f"- \"{item['raw_title']}\" — 오픈 일시 형식 인식 실패")
        lines.append("")

    # 매칭 실패
    if match_failures:
        lines.append(f"■ 매칭 실패 {len(match_failures)}건 (공연명 추정 불가):")
        for item in match_failures:
            lines.append(f"- \"{item['raw_title']}\" — podor 공연 목록에서 유사 공연명 못 찾음")
        lines.append("")

    # 이미 등록됨
    if duplicates:
        lines.append(f"■ 이미 등록됨 {len(duplicates)}건 (스킵)")
        lines.append("")

    # 어린이 뮤지컬 제외
    if kids_excluded:
        lines.append(f"■ 어린이 뮤지컬 제외 {len(kids_excluded)}건:")
        names = ", ".join(item["raw_title"] for item in kids_excluded)
        lines.append(f"- {names}")
        lines.append("")

    # 아무 내용도 없으면
    if not any([new_items, unregistered_performances, unregistered_seasons,
                parse_failures, match_failures, duplicates, kids_excluded]):
        lines.append("수집 결과 없음 (스크래핑 오류 가능성이 있습니다. 확인 필요)")

    return "\n".join(lines)


def send_email(subject: str, body: str) -> bool:
    """Gmail SMTP로 메일 발송. 실패 시 False 반환."""
    try:
        msg = MIMEMultipart()
        msg["From"] = SMTP_EMAIL
        msg["To"] = NOTIFY_EMAIL
        msg["Subject"] = subject

        msg.attach(MIMEText(body, "plain", "utf-8"))

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(SMTP_EMAIL, SMTP_PASSWORD)
            server.sendmail(SMTP_EMAIL, NOTIFY_EMAIL, msg.as_string())

        logger.info(f"Email sent to {NOTIFY_EMAIL}")
        return True
    except Exception as e:
        logger.error(f"Email send failed: {e}")
        return False
