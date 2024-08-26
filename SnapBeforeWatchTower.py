#!/usr/bin/python3

import re
import subprocess
import datetime
import argparse
import shutil
import sys
import os
import logging
import glob

class CustomLogger(logging.Logger):
    def __init__(self, name, log_filename):
        super().__init__(name)

        # Set up formatter for log messages
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

        # Set up log file handler
        file_handler = logging.FileHandler(log_filename)
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        self.addHandler(file_handler)

        # Set up console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        self.addHandler(console_handler)
        
def setup_logger(log_folder, log_date):
    global err_filepath  # Use the global variable
    log_filename = f"SnapBeforeWatchTower-Date-{log_date}.log"
    log_filepath = os.path.join(log_folder, log_filename)

    # Set up logger for normal output
    logger = CustomLogger("SnapBeforeWatchTower", log_filepath)

    # Set the logger level
    logger.setLevel(logging.DEBUG)

    # Set up logger for errors
    err_filename = f"SnapBeforeWatchTower-Date-{log_date}.err"
    err_filepath = os.path.join(log_folder, err_filename)
    error_logger = CustomLogger("SnapBeforeWatchTowerError", err_filepath)

    # Set the error logger level
    error_logger.setLevel(logging.ERROR)

    return logger, error_logger

def get_newest_files(log_dir, prefix):
    files = glob.glob(os.path.join(log_dir, f"{prefix}*"))
    files.sort(key=os.path.getctime, reverse=True)
    
    newest_log = None
    newest_err = None

    for file in files:
        ext = os.path.splitext(file)[-1][1:]  # Get the file extension without the dot
        if ext == "log" and not newest_log:
            newest_log = file
        elif ext == "err" and not newest_err:
            newest_err = file
        
        if newest_log and newest_err:
            break

    return newest_log, newest_err

# This is is for the send mail part
def send_mail(subject, body, recipient, attachment_files=None):
    mail_command = ['mail', '-s', subject, recipient]

    if attachment_files:
        for file in attachment_files:
            mail_command.extend(['--attach', file])
    print("Mail command : ", mail_command)
    process = subprocess.Popen(mail_command, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    _, stderr_output = process.communicate(input=body.encode())

    mail_exit_code = process.returncode

    return mail_exit_code, stderr_output.decode().strip()

# This is for the send mail function
# In case one needs to be notified of errors
#
# FIx and make sure to make it possible to send error message even if .out file is not created yet
def MailTo(logger, error_logger, recipient):
    log_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
    
    print_separator(logger)

    logger.info('There is an option to send a mail')

    # Define subject
    subject = "Error snapshotting or cleaning up snapshots/logs - attaching logs"

    # Get the latest .log and .err files
    newest_log, newest_err = get_newest_files(log_folder, "SnapBeforeWatchTower")
    attachment_files = []
    
    # Start by creating an empty body
    body = ""
    
    # Add the latest .log and .err files to the attachment list
    if newest_log:
        attachment_files.append(newest_log)
    if newest_err:
        attachment_files.append(newest_err)

     # Read contents of .err file
    if os.path.isfile(newest_err):
        with open(newest_err, 'r') as err_file:
            err_contents = err_file.read()
            body += "----------\n\n.err file\n" + err_contents

    # Read contents of .log file
    if os.path.isfile(newest_log):
        with open(newest_log, 'r') as log_file:
            log_contents = log_file.read()
            body += "----------\n\n.log file\n" + log_contents

    # Send the Mail
    mail_exit_code, stderr_output = send_mail(subject, body, recipient, attachment_files)
                
    if mail_exit_code == 0:
        WasMailSent(logger, error_logger, 0, "")
    else:
        WasMailSent(logger, error_logger, mail_exit_code, stderr_output)

def WasMailSent(logger, error_logger, MailExitCode, popenstderr):
    if MailExitCode == 0:
        print_separator(logger)
        logger.info('Mail was send succesfully')
    else:
        print_separator(logger, error_logger)
        error_logger.error('There was an error sending the mail')
        error_logger.error('This is what popen said')
        error_logger.error('')
        error_logger.error(popenstderr)
        error_logger.error('')
        error_logger.error('----------')

def parse_older_than(value):
    pattern = r'^(\d+)([dwm])$'
    match = re.match(pattern, value)
    if not match:
        raise argparse.ArgumentTypeError("Invalid value for --older-than. Use format 'Nd', 'Nw', or 'Nm' (N=integer).")

    num = int(match.group(1))
    unit = match.group(2)

    if unit == 'd':
        return datetime.timedelta(days=num)
    elif unit == 'w':
        return datetime.timedelta(weeks=num)
    elif unit == 'm':
        return datetime.timedelta(days=num * 30)  # Calculate based on 30 days per month
    else:
        raise argparse.ArgumentTypeError("Invalid value for --older-than. Use format 'Nd', 'Nw', or 'Nm' (N=integer).")

def create_snapshot(logger, error_logger, dataset):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H_%M_%S")
    snapshot_name = f"SnapBeforeWatchTower-Date-{timestamp}"
    full_snapshot_name = f"{dataset}@{snapshot_name}"
    logger.info(f"Creating snapshot of: {dataset}")
    logger.debug(f"Full snapshot name: {full_snapshot_name}")

    try:
        subprocess.run(["zfs", "snapshot", full_snapshot_name], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, check=True)
    except subprocess.CalledProcessError as e:
        print_separator(logger, error_logger)
        error_logger.error(f"Error creating snapshot of {dataset}. Command output: {e.stderr.strip()}")
        raise e

def extract_snapshot_date(snapshot_name):
    # Assuming the snapshot name has the format 'SnapBeforeWatchTower-Date2023-05-28_09_33_17'
    date_str = snapshot_name.split('Date', 1)[-1]
    return datetime.datetime.strptime(date_str, "%Y-%m-%d_%H_%M_%S")

def is_older_than(logger, error_logger, snapshot_date_str, older_than):
    try:
        # Convert the snapshot date string to a datetime object
        snapshot_date = datetime.datetime.strptime(snapshot_date_str, "%Y-%m-%d_%H_%M_%S")
        today = datetime.datetime.today()
        age = today - snapshot_date
        return age > older_than
    except ValueError as e:
        # Log error in case of date string formatting issues
        error_logger(f"Date conversion error in is_older_than: {str(e)}")
        return False  # In case of error, assume not older to prevent accidental deletion

   
def delete_old_snapshots(logger, error_logger, dataset, older_than, retain_count):
    global retained_snapshot_dates
    try:
        snapshots = subprocess.check_output(
            ["zfs", "list", "-H", "-t", "snapshot", "-o", "name", dataset],
            stderr=subprocess.PIPE
        ).decode().strip().split("\n")
    except subprocess.CalledProcessError as e:
        error_logger.error(f"Error listing snapshots for {dataset}. Command output: {e.stderr.strip()}")
        return

    retained_snapshot_dates.clear()

    # Updated regex to match both naming conventions
    snap_regex = re.compile(r"SnapBeforeWatchTower-Date-?(\d{4}-\d{2}-\d{2}_\d{2}_\d{2}_\d{2})")

    # Filter snapshots based on the regex
    snapshots = [snapshot for snapshot in snapshots if snap_regex.search(snapshot)]

    # Categorize snapshots into newer and older using the flexible date extraction
    try:
        newer_snapshots = [snapshot for snapshot in snapshots
                           if not is_older_than(logger, error_logger, snap_regex.search(snapshot).group(1), older_than)]
        older_snapshots = [snapshot for snapshot in snapshots
                           if is_older_than(logger, error_logger, snap_regex.search(snapshot).group(1), older_than)]
    except Exception as e:
        error_logger.error(f"Error processing snapshot dates: {str(e)}")
        return

    if len(newer_snapshots) >= retain_count:
        to_delete = older_snapshots
    else:
        total_snapshots = len(newer_snapshots) + len(older_snapshots)
        if total_snapshots <= retain_count:
            retained_snapshot_dates += [snap_regex.search(s).group(1) for s in newer_snapshots + older_snapshots]
            return
        retain_older_count = retain_count - len(newer_snapshots)
        to_delete = older_snapshots[retain_older_count:]
        retained_snapshot_dates += [snap_regex.search(s).group(1) for s in newer_snapshots + older_snapshots[retain_older_count:]]

    for snapshot_name in to_delete:
        try:
            subprocess.run(["zfs", "destroy", snapshot_name], check=True)
            logger.info(f"Deleted snapshot: {snapshot_name}")
        except subprocess.CalledProcessError as e:
            error_logger.error(f"Error deleting snapshot {snapshot_name}. Command output: {e.stderr.strip()}")

    # Update the global list with dates of snapshots that were not deleted
    retained_snapshot_dates += [snap_regex.search(s).group(1) for s in snapshots if s not in to_delete]




def get_log_folder():
    # This function returns the path to the logs directory located in the same directory as the script.
    script_dir = os.path.dirname(os.path.abspath(__file__))  # Get the directory where the script is located.
    log_folder = os.path.join(script_dir, "logs")  # Path to the logs directory.
    return log_folder

def group_files_by_date(log_folder, date_pattern):
    files_by_date = {}
    for filename in os.listdir(log_folder):
        match = date_pattern.search(filename)
        if match:
            date_key = match.group(1)
            if date_key not in files_by_date:
                files_by_date[date_key] = []
            files_by_date[date_key].append(filename)
    return files_by_date

# Global list to keep dates of retained snapshots
retained_snapshot_dates = []

def delete_old_files(logger, error_logger, log_folder, older_than, retain_count):
    # older_than is already a datetime.timedelta object, no need to parse

    # Regex to match both "Date" and "Date-" formats in the filename
    date_pattern = re.compile(r"SnapBeforeWatchTower[-_][Dd]ate[-_]?(\d{4}-\d{2}-\d{2}_\d{2}_\d{2}_\d{2})\.(log|err|digest)")

    files_by_date = {}
    for filename in os.listdir(log_folder):
        match = date_pattern.search(filename)
        if match:
            date_key = match.group(1)
            if date_key not in files_by_date:
                files_by_date[date_key] = []
            files_by_date[date_key].append(filename)

    dated_files = {datetime.datetime.strptime(date, "%Y-%m-%d_%H_%M_%S"): files for date, files in files_by_date.items()}
    sorted_dates = sorted(dated_files.keys())

    cutoff_date = datetime.datetime.now() - older_than

    eligible_for_deletion = [date for date in sorted_dates if date < cutoff_date]

    if len(sorted_dates) - len(eligible_for_deletion) < retain_count:
        to_retain = retain_count - (len(sorted_dates) - len(eligible_for_deletion))
        eligible_for_deletion = eligible_for_deletion[:-to_retain]

    files_to_delete = [file for date in eligible_for_deletion for file in dated_files[date]]

    for filename in files_to_delete:
        path_to_file = os.path.join(log_folder, filename)
        try:
            os.remove(path_to_file)
            logger.info(f"Deleted file: {filename}")
        except Exception as e:
            error_logger.error(f"Failed to delete file: {filename}. Error: {str(e)}")

def print_separator(logger, error_logger=None):
    separator_length = 20
    separator = "\n" + "\n" + "-" * separator_length + "\n"
    
    if error_logger:
        error_logger.error(separator)
    else:
        logger.info(separator)
        
def save_docker_image_digests():
    log_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
    os.makedirs(log_folder, exist_ok=True)
    filename = f"SnapBeforeWatchTower-Date-{datetime.datetime.now().strftime('%Y-%m-%d_%H_%M_%S')}.digest"
    filepath = os.path.join(log_folder, filename)
    with open(filepath, "w") as file:
        subprocess.run(["docker", "images", "--digests"], stdout=file)

def main():
    global err_filepath  # Use the global variable
    parser = argparse.ArgumentParser(description='Create or delete snapshots for ZFS datasets.')
    parser.add_argument('-c', '--command', choices=['create', 'delete'], required=True, help='Command: create or delete')
    parser.add_argument('-f', '--file', required=True, help='Path to the file containing the dataset names')
    parser.add_argument('--older-than', type=parse_older_than, required=True, help="Delete snapshots older than 'Nd', 'Nw', or 'Nm' (N=integer)")
    parser.add_argument('--retain-count', type=int, required=True, help='Number of snapshots to retain despite being older')
    parser.add_argument('--send-mail', metavar='EMAIL', help='Send an email notification to the specified email address')
    
    args = parser.parse_args()

    log_date = datetime.datetime.now().strftime('%Y-%m-%d_%H_%M_%S')
    log_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
    os.makedirs(log_folder, exist_ok=True)

    # Create separate loggers for main logs and error logs
    logger, error_logger = setup_logger(log_folder, log_date)

    with open(args.file, "r") as file:
        datasets = file.read().splitlines()

    try:
        if args.command == 'create':
            save_docker_image_digests()
            print_separator(logger)
            logger.info("Starting snapshot creation...")
            for dataset in datasets:
                print_separator(logger)
                create_snapshot(logger, error_logger, dataset)
                delete_old_snapshots(logger, error_logger, dataset, args.older_than, args.retain_count)
            print_separator(logger)
            logger.info("Snapshot creation completed.")
            delete_old_files(logger, error_logger, log_folder, args.older_than, args.retain_count)

        elif args.command == 'delete':
            print_separator(logger)
            logger.info("Starting snapshot deletion...")
            for dataset in datasets:
                delete_old_snapshots(logger, error_logger, dataset, args.older_than, args.retain_count)
            print_separator(logger)
            logger.info("Snapshot deletion completed.")
            delete_old_files(logger, error_logger, log_folder, args.older_than, args.retain_count)

    except Exception as e:
        print_separator(logger, error_logger)
        error_logger.exception("An error occurred:")
        print_separator(logger, error_logger)
        if args.send_mail:
            MailTo(logger, error_logger, args.send_mail)

    finally:
        # Check if the .err file is empty, and remove it if it is
        if os.path.exists(err_filepath) and os.path.getsize(err_filepath) == 0:
            os.remove(err_filepath)

if __name__ == "__main__":
    main()
