import time
from options.train_options import TrainOptions
import data
import models
import wandb
import numpy as np

if __name__ == '__main__':
    opt = TrainOptions().parse()  # get training options

    # 🚀 start a run, with a type to label it and a project it can call home
    with wandb.init(project="CellEnMon_CycleGan", job_type="load-data") as run:
        dataset = data.create_dataset(opt)  # create a dataset given opt.dataset_mode and other options

        # 🏺 create our Artifact
        raw_data=wandb.Artifact(
            "CellEnMon_CycleGan_Dataset", type="dataset",
            description="raw dataset of ims and dme stations",
            metadata={
                "dme_shape": dataset.A_size,
                "ims_shape": dataset.B_size
            }
        )

        with raw_data.new_file("dataset.npz", mode="wb") as file:
            # 🐣 Store a new file in the artifact, and write something into its contents.
            np.savez(file,x=dataset.dataset.dme_data, y=dataset.dataset.ims_data)

        # ✍️ Save the artifact to W&B.
        run.log_artifact(raw_data)

    preprocessed_steps={

    }
    with wandb.init(project="CellEnMon_CycleGan", job_type="preprocess-data") as run:
        processsed_data=wandb.Artifiact(
            "CellEnMon_CycleGan_Dataset_preprocessed", type="dataset",
            description="processed CellEnMon_CycleGan_Dataset",
            metadata=preprocessed_steps
        )

        # ✔️ declare which artifact we'll be using
        raw_data_artifact = run.use_artifact('mnist-raw:latest')


    dataset_size = len(dataset)  # get the number of images in the dataset.
    print('The number of training images = %d' % dataset_size)

    model = models.create_model(opt)  # create a model given opt.model and other options
    model.setup(opt)  # regular setup: load and print networks; create schedulers
    total_iters = 0  # the total number of training iterations

    for epoch in range(opt.epoch_count,
                       opt.n_epochs + opt.n_epochs_decay + 1):  # outer loop for different epochs; we save the model by <epoch_count>, <epoch_count>+<save_latest_freq>
        epoch_start_time = time.time()  # timer for entire epoch
        iter_data_time = time.time()  # timer for data loading per iteration
        epoch_iter = 0  # the number of training iterations in current epoch, reset to 0 every epoch
        model.update_learning_rate()  # update learning rates in the beginning of every epoch.
        for i, data in enumerate(dataset):  # inner loop within one epoch
            iter_start_time = time.time()  # timer for computation per iteration
            if total_iters % opt.print_freq == 0:
                t_data = iter_start_time - iter_data_time

            total_iters += opt.batch_size
            epoch_iter += opt.batch_size
            model.set_input(data)  # unpack data from dataset and apply preprocessing
            model.optimize_parameters()  # calculate loss functions, get gradients, update network weights

            if total_iters % opt.print_freq == 0:  # print training losses and save logging information to the disk
                losses = model.get_current_losses()
                t_comp = (time.time() - iter_start_time) / opt.batch_size

            if total_iters % opt.save_latest_freq == 0:  # cache our latest model every <save_latest_freq> iterations
                print('saving the latest model (epoch %d, total_iters %d)' % (epoch, total_iters))
                save_suffix = 'iter_%d' % total_iters if opt.save_by_iter else 'latest'
                model.save_networks(save_suffix)

            iter_data_time = time.time()
        if epoch % opt.save_epoch_freq == 0:  # cache our model every <save_epoch_freq> epochs
            print('saving the model at the end of epoch %d, iters %d' % (epoch, total_iters))
            model.save_networks('latest')
            model.save_networks(epoch)

        wandb.log(losses)
        print('End of epoch %d / %d \t Time Taken: %d sec' % (
        epoch, opt.n_epochs + opt.n_epochs_decay, time.time() - epoch_start_time))
